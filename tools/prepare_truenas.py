"""Prepare TrueNAS iPXE assets from the checksum-pinned official installer ISO.

Requires Python 3 and 7-Zip. Does not install TrueNAS or publish assets.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

VERSION = '25.10.7'
ISO_NAME = f'TrueNAS-SCALE-{VERSION}.iso'
ISO_URL = f'https://download.sys.truenas.net/TrueNAS-SCALE-Goldeye/{VERSION}/{ISO_NAME}'
ISO_SHA256 = '54ce9441ce66966a392e28f63604ca3c2c083d0bec4db7bb5af2f74f7a007c8e'
HOOK = Path(__file__).resolve().parents[1] / 'truenas' / 'netboot-media'


def media_archive(script, order):
    """Root-owned, deterministic newc overlay for initramfs-tools."""
    archive = bytearray()
    entries = [('scripts/init-bottom/truenas-netboot', script, 0o100755),
               ('scripts/init-bottom/ORDER', order + b'\n/scripts/init-bottom/truenas-netboot "$@"\n', 0o100644),
               ('TRAILER!!!', b'', 0)]
    for inode, (name, data, mode) in enumerate(entries, 1):
        name = name.encode('ascii') + b'\0'
        fields = [inode, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name), 0]
        archive.extend(b'070701' + ''.join(f'{v:08x}' for v in fields).encode() + name)
        archive.extend(b'\0' * (-len(archive) % 4))
        archive.extend(data)
        archive.extend(b'\0' * (-len(archive) % 4))
    return archive


def prepare(output, iso=None, seven_zip='7z'):
    output.mkdir(parents=True, exist_ok=False)
    if iso is None:
        iso = output / ISO_NAME
        urllib.request.urlretrieve(ISO_URL, iso)
    with iso.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest != ISO_SHA256:
        raise ValueError('TrueNAS ISO checksum mismatch; extraction refused')
    extracted = output / 'extracted'
    subprocess.run([seven_zip, 'x', '-y', '-o' + str(extracted), str(iso),
                    'vmlinuz', 'initrd.img', 'boot/grub/grub.cfg'], check=True)
    config = (extracted / 'boot/grub/grub.cfg').read_text()
    if 'boot=live' not in config or '/initrd.img' not in config:
        raise ValueError('Unexpected installer boot configuration')
    shutil.copyfile(extracted / 'vmlinuz', output / 'truenas-vmlinuz')
    # initramfs-tools runs only the scripts listed in ORDER. Preserve its
    # original commands (including udev cleanup), then append our media hook.
    unpacked = output / 'original-initrd'
    subprocess.run([seven_zip, 'x', '-y', '-o' + str(unpacked),
                    str(extracted / 'initrd.img')], check=True)
    subprocess.run([seven_zip, 'e', '-y', '-o' + str(unpacked),
                    str(unpacked / 'initrd'), 'scripts/init-bottom/ORDER'], check=True)
    order = (unpacked / 'ORDER').read_bytes()
    if b'/scripts/init-bottom/udev' not in order:
        raise ValueError('Unexpected initramfs cleanup order')
    target = output / 'truenas-initrd'
    shutil.copyfile(extracted / 'initrd.img', target)
    with target.open('ab') as stream:
        stream.write(b'\0' * (-stream.tell() % 4))
        stream.write(media_archive(HOOK.read_bytes().replace(b'\r\n', b'\n'), order))
    hashes = {}
    for path in sorted(output.glob('truenas-*')):
        with path.open('rb') as source:
            hashes[path.name] = hashlib.file_digest(source, 'sha256').hexdigest()
    (output / 'SHA256SUMS').write_text(''.join(f'{h}  {n}\n' for n, h in hashes.items()), encoding='ascii')
    (output / 'source.json').write_text(json.dumps({
        'version': VERSION, 'iso_url': ISO_URL, 'iso_sha256': digest,
        'assets_sha256': hashes,
        'modification': 'init-bottom hook binds fetched installer media to /cdrom',
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--iso', type=Path)
    parser.add_argument('--seven-zip', default='7z')
    args = parser.parse_args()
    prepare(args.output, args.iso, args.seven_zip)
