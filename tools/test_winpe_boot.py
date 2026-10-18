"""Boot WinPE on a disposable QEMU BIOS VM and require its safe startup prompt.

Run on the Linux CI runner with QEMU and Tesseract installed. Never types INSTALL
or starts an OS deployment. All VM disks and logs are in .build/winpe-smoke.
"""
import argparse
import hashlib
import json
import socket
import subprocess
import time
from pathlib import Path

from tools.prepare_small_live import append_cpio


def run(assets):
    work = Path('.build/winpe-smoke').resolve()
    work.mkdir(parents=True, exist_ok=False)
    for line in (assets / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split()
        with (assets / name).open('rb') as source:
            assert hashlib.file_digest(source, 'sha256').hexdigest() == digest
    initrd = work / 'boot.cpio'
    with initrd.open('wb') as stream:
        append_cpio(stream, [assets / name for name in ('BCD', 'boot.sdi', 'boot.wim')])
    disk = work / 'blank-test-disk.qcow2'
    subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(disk), '32G'], check=True)
    sockpath = work / 'qmp.sock'
    command = [
        'qemu-system-x86_64', '-accel', 'tcg,thread=multi', '-cpu', 'max',
        '-smp', '2', '-m', '3072', '-kernel', str(assets / 'wimboot'),
        '-initrd', str(initrd), '-drive', f'file={disk},format=qcow2,if=ide',
        '-nic', 'user,model=e1000', '-vga', 'std', '-display', 'none',
        '-qmp', f'unix:{sockpath},server=on,wait=off', '-no-reboot',
    ]
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
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets', type=Path)
    args = parser.parse_args()
    run(args.assets.resolve())
