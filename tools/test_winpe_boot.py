"""Boot WinPE through iPXE and verify storage, networking and PowerShellGet.

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
import tempfile
import threading
import time
from pathlib import Path

def run(assets, firmware='bios', memory=8192, devices='sata', boot_source='netboot'):
    work = Path(f'.build/winpe-smoke-{boot_source}-{firmware}-{devices}').resolve()
    work.mkdir(parents=True, exist_ok=False)
    for line in (assets / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split()
        with (assets / name).open('rb') as source:
            assert hashlib.file_digest(source, 'sha256').hexdigest() == digest
    if boot_source == 'iso':
        # Verify artifact parity by reading the actual WIM from the published ISO.
        extractor = subprocess.Popen(['7z', 'x', '-so', '-ssc-', str(assets / 'osdcloud.iso'), 'sources/boot.wim'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        embedded_hash = hashlib.file_digest(extractor.stdout, 'sha256').hexdigest()
        extractor.stdout.close()
        extractor.wait(timeout=30)
        stderr = extractor.stderr.read()
        if extractor.returncode != 0:
            raise RuntimeError(f'Cannot read ISO boot.wim: {stderr.decode(errors="replace")}')
        with (assets / 'boot.wim').open('rb') as source:
            if embedded_hash != hashlib.file_digest(source, 'sha256').hexdigest():
                raise RuntimeError('ISO/netboot WIM mismatch')
    network_probe_received = threading.Event()
    osd_download_received = threading.Event()

    class BootFileHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            super().do_GET()
            if self.path == '/network-probe.txt':
                network_probe_received.set()
            if self.path == '/download-probe.txt':
                osd_download_received.set()

    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(BootFileHandler, directory=str(assets)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://10.0.2.2:{server.server_port}'
    (assets / 'network-probe.txt').write_text('WINPE-NETWORK-POWERSHELLGET-PASS')
    (assets / 'download-probe.txt').write_text('WINPE-OSD-DOWNLOAD-PASS')
    tftp = work / 'tftp'
    tftp.mkdir()
    script = (f'#!ipxe\ndhcp || goto failed\nkernel {base}/wimboot || goto failed\n' +
              ''.join(f'initrd --name {name} {base}/{name} {name} || goto failed\n'
                      for name in ('BCD', 'boot.sdi', 'boot.wim')) +
              'boot || goto failed\n:failed\necho WinPE boot test failed in iPXE\nshell\n')
    (tftp / 'boot.ipxe').write_text(script)
    disk = work / 'blank-test-disk.qcow2'
    subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(disk), '32G'], check=True)
    socket_dir = tempfile.TemporaryDirectory(prefix='osd-qmp-')
    sockpath = Path(socket_dir.name) / 'qmp.sock'
    kvm = os.path.exists('/dev/kvm') and os.access('/dev/kvm', os.W_OK)
    command = [
        'qemu-system-x86_64', '-machine', 'q35',
        '-accel', 'kvm' if kvm else 'tcg,thread=multi', '-cpu', 'host' if kvm else 'max',
        '-smp', '2', '-m', str(memory),
        '-vga', 'std', '-display', 'none',
        '-qmp', f'unix:{sockpath},server=on,wait=off', '-no-reboot',
    ]
    nic = 'e1000' if devices == 'sata' else 'vmxnet3' if devices == 'vmware' else 'virtio-net-pci'
    command.extend(['-nic', f'user,model={nic},tftp={tftp},bootfile=boot.ipxe'])
    if devices == 'sata':
        command.extend(['-drive', f'file={disk},format=qcow2,if=ide'])
    else:
        command.extend(['-drive', f'file={disk},format=qcow2,if=none,id=testdisk'])
        if devices == 'virtio-blk':
            command.extend(['-device', 'virtio-blk-pci,drive=testdisk'])
        else:
            controller = 'pvscsi' if devices == 'vmware' else 'virtio-scsi-pci'
            command.extend(['-device', f'{controller},id=scsi',
                            '-device', 'scsi-hd,drive=testdisk,bus=scsi.0'])
    if firmware == 'uefi':
        code = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
        variables = work / 'OVMF_VARS.fd'
        shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', variables)
        command.extend(['-drive', f'if=pflash,format=raw,readonly=on,file={code}',
                        '-drive', f'if=pflash,format=raw,file={variables}'])
        if boot_source == 'netboot':
            efi = work / 'efi-boot' / 'EFI' / 'BOOT'
            efi.mkdir(parents=True)
            shutil.copyfile('/usr/lib/ipxe/ipxe.efi', efi / 'BOOTX64.EFI')
            command.extend(['-drive', f'if=none,id=efi,file=fat:rw:{work / "efi-boot"},format=raw',
                            '-device', 'qemu-xhci', '-device', 'usb-storage,drive=efi,bootindex=1'])
    elif boot_source == 'netboot':
        command.extend(['-kernel', '/usr/lib/ipxe/ipxe.lkrn'])
    if boot_source == 'iso':
        command.extend(['-cdrom', str(assets / 'osdcloud.iso'), '-boot', 'order=d'])
    (work / 'configuration.txt').write_text(f'Boot: {boot_source}\nFirmware: {firmware}\nDevices: {devices}\nRAM: {memory} MB\nKVM: {kvm}\n')
    print(f'Boot test: {boot_source}, {firmware}, devices={devices}, {memory} MB RAM, KVM={kvm}', flush=True)
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
                if boot_source == 'iso':
                    # Accommodate Microsoft's optional CD "press any key" prompt.
                    for _ in range(20):
                        time.sleep(1)
                        prompt = work / 'cd-prompt.png'
                        qmp('screendump', {'filename': str(prompt), 'format': 'png'})
                        prompt_text = subprocess.check_output(['tesseract', str(prompt), 'stdout'], stderr=subprocess.DEVNULL, text=True).lower()
                        if 'press any key' in prompt_text and 'boot' in prompt_text:
                            qmp('human-monitor-command', {'command-line': 'sendkey spc'})
                            break
                        if 'osdcloud' in prompt_text:
                            break
                previous = ''
                probe_started = False
                gui_closed = False

                def type_command(text):
                    # US keyboard in the stock en-US WinPE image; no INSTALL is sent.
                    symbols = {' ': 'spc', '-': 'minus', '.': 'dot', '/': 'slash',
                               ':': 'shift-semicolon', ';': 'semicolon', '"': 'shift-apostrophe',
                               '|': 'shift-backslash'}
                    symbols.update({'$': 'shift-4', "'": 'apostrophe', '=': 'equal'})
                    for character in text:
                        key = symbols.get(character, character)
                        qmp('human-monitor-command', {'command-line': f'sendkey {key} 20'})
                        time.sleep(0.045)
                    qmp('human-monitor-command', {'command-line': 'sendkey ret'})

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
                    gui_visible = ('deployment options' in normalized and
                                   'osdcloudgui' in normalized.replace('0sdcloudgui', 'osdcloudgui'))
                    if not probe_started and not gui_closed and gui_visible:
                        shutil.copyfile(screenshot, work / 'initial-gui.png')
                        (work / 'initial-gui.txt').write_text(text)
                        # Close without clicking Start; keep this a read-only boot test.
                        qmp('human-monitor-command', {'command-line': 'sendkey alt-f4'})
                        time.sleep(3)
                        qmp('human-monitor-command', {'command-line': 'sendkey alt-tab'})
                        time.sleep(1)
                        qmp('human-monitor-command', {'command-line': 'sendkey alt-spc'})
                        time.sleep(1)
                        qmp('human-monitor-command', {'command-line': 'sendkey x'})
                        gui_closed = True
                        continue
                    legacy_prompt = 'type install' in normalized and 'osdcloud' in normalized
                    if not probe_started and (legacy_prompt or (gui_closed and 'returned to winpe' in normalized)):
                        # Older releases have a text gate; new releases open their GUI directly.
                        # Getting this far proves Get-Disk saw the only attached test disk.
                        if legacy_prompt:
                            qmp('human-monitor-command', {'command-line': 'sendkey ret'})
                            time.sleep(2)
                        type_command('powershell -nop -ep bypass -c "$erroractionpreference=\'stop\'; '
                                     'import-module powershellget -requiredversion 2.2.5 -ea stop; '
                                     'import-packageprovider nuget -minimumversion 2.8.5.201 -ea stop | out-null; '
                                     'find-module osd -requiredversion 26.10.6.1 -ea stop | out-null; '
                                     'import-module osd -requiredversion 26.10.6.1 -ea stop; '
                                     f'save-webfile -sourceurl {base}/download-probe.txt '
                                     '-destinationdirectory x:/osd-smoke -destinationname probe.txt -webclient -ea stop | out-null; '
                                     f'irm {base}/network-probe.txt"')
                        probe_started = True
                    # Use the actual HTTP request rather than OCR of its result.
                    # Small console glyphs can turn WINPE into JINPE in Tesseract.
                    if probe_started and network_probe_received.is_set() and osd_download_received.is_set():
                        print('PASS: Test disk visible, HTTP networking, PowerShellGet/NuGet/Find-Module and OSD WebClient download work. No deployment started.', flush=True)
                        return
                    if not probe_started and not gui_closed and 'returned to winpe' in normalized:
                        raise RuntimeError('WinPE launcher failed before opening its GUI; see screenshot')
                    if 'running scripts is disabled' in normalized or 'could not be loaded' in normalized:
                        raise RuntimeError('A PowerShell module failed to load; see screenshot')
                    if '0xc000000f' in normalized or 'boot configuration data' in normalized:
                        raise RuntimeError('Windows Boot Manager rejected the boot configuration')
            raise TimeoutError('WinPE did not finish the read-only GUI/network probe; see screenshot')
        finally:
            server.shutdown()
            server.server_close()
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            socket_dir.cleanup()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets', type=Path)
    parser.add_argument('--firmware', choices=('bios', 'uefi'), default='bios')
    parser.add_argument('--memory', type=int, default=8192)
    parser.add_argument('--boot', choices=('netboot', 'iso'), default='netboot')
    parser.add_argument('--devices', choices=('sata', 'virtio-scsi', 'virtio-blk', 'vmware'), default='sata')
    args = parser.parse_args()
    run(args.assets.resolve(), args.firmware, args.memory, args.devices, args.boot)
