"""Deploy Windows through the actual OSDCloud GUI to a disposable CI-only VM.

This is deliberately separate from the non-destructive boot smoke test. Both the
host and guest validate dedicated test-only conditions before any disk clear.
Never runs on the user's machine; requires a GitHub-hosted runner and KVM.
"""
import csv
import io
import re
import struct
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

def run(assets, firmware='uefi', memory=8192, devices='virtio-scsi', boot_source='netboot', os_version='windows11'):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
        raise RuntimeError('Full deployment is restricted to disposable GitHub-hosted runners.')
    if not (os.path.exists('/dev/kvm') and os.access('/dev/kvm', os.W_OK)):
        raise RuntimeError('The full deployment test requires KVM.')
    work = Path(f'.build/winpe-deploy-{os_version}-{boot_source}-{firmware}-{devices}').resolve()
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
    evidence = work / 'evidence'
    evidence.mkdir()
    reports = {}
    network_probe_received = threading.Event()
    osd_download_received = threading.Event()

    class BootFileHandler(SimpleHTTPRequestHandler):
        def do_POST(self):
            match = re.fullmatch(r'/evidence/([a-zA-Z0-9_.-]+)', self.path)
            size = int(self.headers.get('Content-Length', '0'))
            if not match or size < 0 or size > 30 * 1024 * 1024:
                self.send_error(400)
                return
            data = self.rfile.read(size)
            (evidence / match.group(1)).write_bytes(data)
            if match.group(1).endswith('.json'):
                try:
                    reports[match.group(1)] = json.loads(data.decode('utf-8-sig'))
                except (ValueError, UnicodeError):
                    pass
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

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
    shutil.copyfile(Path(__file__).resolve().parent / 'winpe-ci' / 'Start-DeploymentTest.ps1', assets / 'ci-deploy.ps1')
    tftp = work / 'tftp'
    tftp.mkdir()
    script = (f'#!ipxe\ndhcp || goto failed\nkernel {base}/wimboot || goto failed\n' +
              ''.join(f'initrd --name {name} {base}/{name} {name} || goto failed\n'
                      for name in ('BCD', 'boot.sdi', 'boot.wim')) +
              'boot || goto failed\n:failed\necho WinPE boot test failed in iPXE\nshell\n')
    (tftp / 'boot.ipxe').write_text(script)
    disk = work / 'blank-test-disk.qcow2'
    subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(disk), '80G'], check=True)
    socket_dir = tempfile.TemporaryDirectory(prefix='osd-qmp-')
    sockpath = Path(socket_dir.name) / 'qmp.sock'
    kvm = os.path.exists('/dev/kvm') and os.access('/dev/kvm', os.W_OK)
    command = [
        'qemu-system-x86_64', '-machine', 'q35',
        '-accel', 'kvm' if kvm else 'tcg,thread=multi', '-cpu', 'host' if kvm else 'max',
        '-smp', '2', '-m', str(memory),
        '-smbios', 'type=1,manufacturer=QEMU,product=OSDCloud CI disposable VM,serial=OSDCLOUD-CI-ONLY',
        '-device', 'qemu-xhci,id=ciinput', '-device', 'usb-tablet,bus=ciinput.0',
        '-vga', 'std', '-display', 'none',
        '-qmp', f'unix:{sockpath},server=on,wait=off', '-no-reboot',
    ]
    nic = 'e1000' if devices == 'sata' else 'vmxnet3' if devices == 'vmware' else 'virtio-net-pci'
    command.extend(['-nic', f'user,model={nic},tftp={tftp},bootfile=boot.ipxe'])
    if devices == 'sata':
        command.extend(['-drive', f'file={disk},format=qcow2,if=ide,serial=OSDCLOUD-CI-ONLY'])
    else:
        command.extend(['-drive', f'file={disk},format=qcow2,if=none,id=testdisk'])
        if devices == 'virtio-blk':
            command.extend(['-device', 'virtio-blk-pci,drive=testdisk'])
        else:
            controller = 'pvscsi' if devices == 'vmware' else 'virtio-scsi-pci'
            command.extend(['-device', f'{controller},id=scsi',
                            '-device', 'scsi-hd,drive=testdisk,bus=scsi.0,serial=OSDCLOUD-CI-ONLY'])
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
            deadline = time.monotonic() + 3600
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
                    for _ in range(20):
                        qmp('human-monitor-command', {'command-line': 'sendkey spc'})
                        time.sleep(1)

                def type_command(text):
                    symbols = {' ': 'spc', '-': 'minus', '.': 'dot', '/': 'slash', ':': 'shift-semicolon',
                               ';': 'semicolon', '"': 'shift-apostrophe', '|': 'shift-backslash', '$': 'shift-4',
                               "'": 'apostrophe', '=': 'equal', '&': 'shift-7'}
                    for character in text:
                        key = symbols.get(character, character)
                        qmp('human-monitor-command', {'command-line': f'sendkey {key} 20'})
                        time.sleep(0.045)
                    qmp('human-monitor-command', {'command-line': 'sendkey ret'})

                launched = clicked = confirmed = False
                previous = ''
                while time.monotonic() < deadline:
                    time.sleep(10)
                    if 'failure.json' in reports:
                        raise RuntimeError(f"Guest deployment failed: {reports['failure.json']}")
                    if reports.get('deployment.json', {}).get('Completed'):
                        print('Deployment validated. Waiting for WinPE to flush and shut down.', flush=True)
                        process.wait(timeout=120)
                        break
                    if process.poll() is not None:
                        raise RuntimeError('QEMU stopped before the deployment result')
                    screenshot = work / 'screen.png'
                    qmp('screendump', {'filename': str(screenshot), 'format': 'png'})
                    text = subprocess.check_output(['tesseract', str(screenshot), 'stdout'], stderr=subprocess.DEVNULL, text=True)
                    (work / 'screen.txt').write_text(text)
                    normalized = ' '.join(text.lower().split())
                    if normalized != previous:
                        print(text[-1900:], flush=True)
                        previous = normalized
                    if not launched and 'type install' in normalized and 'osdcloud' in normalized:
                        qmp('human-monitor-command', {'command-line': 'sendkey ret'})
                        time.sleep(2)
                        type_command('powershell -nop -ep bypass -c "'
                                     f'iwr -usebasicparsing {base}/ci-deploy.ps1 -outfile x:/ci-deploy.ps1; '
                                     f'& x:/ci-deploy.ps1 -server {base} -os {os_version} -devices {devices}"')
                        launched = True
                    if launched and not clicked and reports.get('ready.json', {}).get('GuardPassed') and 'operating system' in normalized:
                        tsv = subprocess.check_output(['tesseract', str(screenshot), 'stdout', 'tsv'], stderr=subprocess.DEVNULL, text=True)
                        width, height = struct.unpack('>II', screenshot.read_bytes()[16:24])
                        buttons = [row for row in csv.DictReader(io.StringIO(tsv), delimiter='\t')
                                   if row['text'].strip().lower() == 'start' and int(row['left']) > width * 0.4 and int(row['top']) > height * 0.4]
                        if buttons:
                            button = max(buttons, key=lambda row: int(row['top']))
                            x = int(button['left']) + int(button['width']) // 2
                            y = int(button['top']) + int(button['height']) // 2
                            qmp('input-send-event', {'events': [
                                {'type': 'abs', 'data': {'axis': 'x', 'value': x * 32767 // width}},
                                {'type': 'abs', 'data': {'axis': 'y', 'value': y * 32767 // height}}]})
                            qmp('input-send-event', {'events': [{'type': 'btn', 'data': {'button': 'left', 'down': True}}]})
                            qmp('input-send-event', {'events': [{'type': 'btn', 'data': {'button': 'left', 'down': False}}]})
                            clicked = True
                            print('Clicked the actual OSDCloud GUI Start button after the blank CI disk guard.', flush=True)
                    if clicked and not confirmed and 'clear-disk' in normalized and 'disk 0' in normalized and 'confirm' in normalized:
                        # The guest guard and fresh qcow2 ensure this can only erase the CI test disk.
                        type_command('y')
                        confirmed = True
                        print('Confirmed clearing the single disposable CI disk.', flush=True)
                    if not launched and 'returned to winpe' in normalized:
                        raise RuntimeError('WinPE prerequisite validation failed before deployment')
                else:
                    raise TimeoutError('OSDCloud did not complete the deployment within one hour')

            # Start the deployed Windows from the same disk with all PE boot sources removed.
            os_command = []
            index = 0
            while index < len(command):
                item = command[index]
                if item == '-no-reboot':
                    # Windows setup legitimately reboots before reaching OOBE.
                    index += 1
                    continue
                if item in ('-kernel', '-cdrom', '-boot'):
                    index += 2
                    continue
                if item == '-drive' and 'id=efi,' in command[index + 1]:
                    index += 2
                    continue
                if item == '-device' and command[index + 1] in ('qemu-xhci', 'usb-storage,drive=efi,bootindex=1'):
                    index += 2
                    continue
                os_command.append(item)
                index += 1
            os_command.extend(['-boot', 'order=c'])
            if sockpath.exists():
                sockpath.unlink()
            process = subprocess.Popen(os_command, stdout=log, stderr=log)
            until = time.monotonic() + 1200
            while not sockpath.exists():
                if process.poll() is not None or time.monotonic() > until:
                    raise RuntimeError('The deployed OS VM failed to start')
                time.sleep(1)
            with socket.socket(socket.AF_UNIX) as os_connection:
                os_connection.connect(str(sockpath))
                reader = os_connection.makefile('rwb', buffering=0)
                reader.readline()
                qmp('qmp_capabilities')
                while time.monotonic() < until:
                    time.sleep(15)
                    if process.poll() is not None:
                        raise RuntimeError('The installed Windows stopped before OOBE')
                    screenshot = work / 'installed-os.png'
                    qmp('screendump', {'filename': str(screenshot), 'format': 'png'})
                    text = subprocess.check_output(['tesseract', str(screenshot), 'stdout'], stderr=subprocess.DEVNULL, text=True)
                    (work / 'installed-os.txt').write_text(text)
                    normalized = ' '.join(text.lower().split())
                    print(text[-1000:], flush=True)
                    if any(marker in normalized for marker in ('country or region', 'keyboard layout', "start with region")):
                        result = dict(reports['deployment.json'], InstalledOSBootedToOOBE=True,
                                      BootSource=boot_source, VMFirmware=firmware)
                        (work / 'result.json').write_text(json.dumps(result, indent=2))
                        print('PASS: actual OSDCloud GUI deployment, installed Windows and target boot verified to OOBE.', flush=True)
                        return
                raise TimeoutError('Installed Windows did not reach OOBE')
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
    parser.add_argument('--firmware', choices=('bios', 'uefi'), default='uefi')
    parser.add_argument('--memory', type=int, default=8192)
    parser.add_argument('--boot', choices=('netboot', 'iso'), default='netboot')
    parser.add_argument('--devices', choices=('sata', 'virtio-scsi'), default='virtio-scsi')
    parser.add_argument('--os', choices=('windows10', 'windows11'), default='windows11')
    args = parser.parse_args()
    run(args.assets.resolve(), args.firmware, args.memory, args.devices, args.boot, args.os)
