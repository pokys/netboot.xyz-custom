"""Boot WinPE on a disposable QEMU BIOS VM and require its safe startup prompt.

Run on the Linux CI runner with QEMU and Tesseract installed. Never types INSTALL
or starts an OS deployment. All VM disks and logs are in .build/winpe-smoke.
"""
import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

def run(assets, firmware='bios', memory=8192):
    work = Path('.build/winpe-smoke' + ('-uefi' if firmware == 'uefi' else '')).resolve()
    work.mkdir(parents=True, exist_ok=False)
    for line in (assets / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split()
        with (assets / name).open('rb') as source:
            assert hashlib.file_digest(source, 'sha256').hexdigest() == digest
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(assets)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://10.0.2.2:{server.server_port}'
    tftp = work / 'tftp'
    tftp.mkdir()
    script = (f'#!ipxe\ndhcp || goto failed\nkernel {base}/wimboot || goto failed\n' +
              ''.join(f'initrd --name {name} {base}/{name} {name} || goto failed\n'
                      for name in ('BCD', 'boot.sdi', 'boot.wim')) +
              'boot || goto failed\n:failed\necho WinPE boot test failed in iPXE\nshell\n')
    (tftp / 'boot.ipxe').write_text(script)
    disk = work / 'blank-test-disk.qcow2'
    subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(disk), '32G'], check=True)
    sockpath = work / 'qmp.sock'
    kvm = os.path.exists('/dev/kvm') and os.access('/dev/kvm', os.W_OK)
    command = [
        'qemu-system-x86_64', '-machine', 'q35',
        '-accel', 'kvm' if kvm else 'tcg,thread=multi', '-cpu', 'host' if kvm else 'max',
        '-smp', '2', '-m', str(memory), '-drive', f'file={disk},format=qcow2,if=ide',
        '-nic', f'user,model=e1000,tftp={tftp},bootfile=boot.ipxe',
        '-vga', 'std', '-display', 'none',
        '-qmp', f'unix:{sockpath},server=on,wait=off', '-no-reboot',
    ]
    if firmware == 'uefi':
        code = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
        variables = work / 'OVMF_VARS.fd'
        shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', variables)
        efi = work / 'efi-boot' / 'EFI' / 'BOOT'
        efi.mkdir(parents=True)
        shutil.copyfile('/usr/lib/ipxe/ipxe.efi', efi / 'BOOTX64.EFI')
        command.extend(['-drive', f'if=pflash,format=raw,readonly=on,file={code}',
                        '-drive', f'if=pflash,format=raw,file={variables}',
                        '-drive', f'if=none,id=efi,file=fat:rw:{work / "efi-boot"},format=raw',
                        '-device', 'virtio-blk-pci,drive=efi,bootindex=1'])
    else:
        command.extend(['-kernel', '/usr/lib/ipxe/ipxe.lkrn'])
    (work / 'configuration.txt').write_text(f'Firmware: {firmware}\nRAM: {memory} MB\nKVM: {kvm}\n')
    print(f'Boot test: {firmware}, {memory} MB RAM, KVM={kvm}', flush=True)
    with (work / 'qemu.log').open('wb') as log:
        process = subprocess.Popen(command, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 540
            while not sockpath.exists():
                if process.poll() is not None:
                    raise RuntimeError('QEMU failed to start; see qemu.log')
                if time.monotonic() > deadline:
                    raise TimeoutError('QMP socket did not become available')
                time.sleep(1)
            with socket.socket(socket.AF_UNIX) as connection:
                connection.connect(str(sockpath))
                reader = connection.makefile('rwb', buffering=0)
                reader.readline()

                def qmp(name, arguments=None):
                    command = {'execute': name}
                    if arguments:
                        command['arguments'] = arguments
                    reader.write(json.dumps(command).encode() + b'\n')
                    while True:
                        response = json.loads(reader.readline())
                        if 'error' in response:
                            raise RuntimeError(response)
                        if 'return' in response:
                            return response['return']

                qmp('qmp_capabilities')
                previous = ''
                while time.monotonic() < deadline:
                    time.sleep(15)
                    if process.poll() is not None:
                        raise RuntimeError('QEMU exited before the WinPE prompt')
                    screenshot = work / 'screen.png'
                    qmp('screendump', {'filename': str(screenshot), 'format': 'png'})
                    text = subprocess.check_output(['tesseract', str(screenshot), 'stdout'], stderr=subprocess.DEVNULL, text=True)
                    (work / 'screen.txt').write_text(text)
                    normalized = ' '.join(text.lower().split())
                    if normalized != previous:
                        print(text[-1400:], flush=True)
                        previous = normalized
                    if 'type install' in normalized and 'osdcloud' in normalized:
                        print('PASS: WinPE reached interactive OSDCloud confirmation. No deployment started.', flush=True)
                        return
                    if '0xc000000f' in normalized or 'boot configuration data' in normalized:
                        raise RuntimeError('Windows Boot Manager rejected the boot configuration')
            raise TimeoutError('WinPE did not reach its confirmation prompt; see screenshot')
        finally:
            server.shutdown()
            server.server_close()
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets', type=Path)
    parser.add_argument('--firmware', choices=('bios', 'uefi'), default='bios')
    parser.add_argument('--memory', type=int, default=8192)
    args = parser.parse_args()
    run(args.assets.resolve(), args.firmware, args.memory)
