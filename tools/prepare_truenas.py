"""Prepare TrueNAS iPXE assets from the checksum-pinned official installer ISO.

Requires Python 3 and 7-Zip. Does not install TrueNAS or publish assets.
"""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import urllib.request
from pathlib import Path

VERSION = '25.10.7'
ISO_NAME = f'TrueNAS-SCALE-{VERSION}.iso'
ISO_URL = f'https://download.sys.truenas.net/TrueNAS-SCALE-Goldeye/{VERSION}/{ISO_NAME}'
ISO_SHA256 = '54ce9441ce66966a392e28f63604ca3c2c083d0bec4db7bb5af2f74f7a007c8e'
HOOK = Path(__file__).resolve().parents[1] / 'truenas' / 'netboot-media'


def media_archive(script, order, extra=()):
    """Root-owned, deterministic newc overlay for initramfs-tools."""
    archive = bytearray()
    entries = [('scripts/init-bottom/truenas-netboot', script, 0o100755),
               ('scripts/init-bottom/ORDER', order + b'\n/scripts/init-bottom/truenas-netboot "$@"\n', 0o100644),
               *extra, ('TRAILER!!!', b'', 0)]
    for inode, (name, data, mode) in enumerate(entries, 1):
        name = name.encode('ascii') + b'\0'
        fields = [inode, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name), 0]
        archive.extend(b'070701' + ''.join(f'{v:08x}' for v in fields).encode() + name)
        archive.extend(b'\0' * (-len(archive) % 4))
        archive.extend(data)
        archive.extend(b'\0' * (-len(archive) % 4))
    return archive


def elf_dependencies(data):
    """Read ELF64 dependency names without running untrusted guest binaries."""
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Expected little-endian ELF64 binary')
    offset = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    headers = [struct.unpack_from('<IIQQQQQQ', data, offset + i * size) for i in range(count)]
    dynamic = next((h for h in headers if h[0] == 2), None)
    if dynamic is None:
        return []
    tags = [struct.unpack_from('<qQ', data, pos) for pos in range(dynamic[2], dynamic[2] + dynamic[5], 16)]
    strings = next(value for tag, value in tags if tag == 5)
    load = next(h for h in headers if h[0] == 1 and h[3] <= strings < h[3] + h[5])
    start = strings - load[3] + load[2]
    return [data[start + value:data.index(b'\0', start + value)].decode('ascii')
            for tag, value in tags if tag == 1]


def tls_downloader(extracted, seven_zip):
    """Use curl and its exact dependency closure from the checksum-verified ISO."""
    squash = extracted / 'live/filesystem.squashfs'
    def read(path, archive=squash):
        # stdout extraction reads symlink contents without creating Windows links
        # or requesting administrator rights.
        return subprocess.run([seven_zip, 'x', '-so', str(archive), path],
                              check=True, capture_output=True).stdout
    def library(name):
        data = read('usr/lib/x86_64-linux-gnu/' + name)
        if data[:4] != b'\x7fELF':
            data = read('usr/lib/x86_64-linux-gnu/' + data.decode('ascii'))
        return data
    curl = read('usr/bin/curl')
    pending = elf_dependencies(curl)
    dependencies = {}
    while pending:
        name = pending.pop()
        if name in dependencies:
            continue
        data = library(name)
        dependencies[name] = data
        pending.extend(elf_dependencies(data))
    dependencies['ld-linux-x86-64.so.2'] = library('ld-linux-x86-64.so.2')
    mount_path = 'usr/lib/live/boot/9990-mount-http.sh'
    mount_script = read(mount_path, extracted.parent / 'original-initrd/initrd')
    invocation = b'wget "${url}" -O "${dest}/$(basename ${url})"'
    if mount_script.count(invocation) != 1:
        raise ValueError('Unexpected live-boot downloader invocation')
    mount_script = mount_script.replace(invocation, b'/opt/truenas-netboot/wget "${url}" -O "${dest}/$(basename ${url})" || return 1')
    wrapper = b'''#!/bin/sh
set -eu
# Debian live-boot invokes exactly: wget URL -O DESTINATION.
[ "$#" -eq 3 ] && [ "$2" = -O ] || exit 2
exec /opt/truenas-netboot/lib/ld-linux-x86-64.so.2 --library-path /opt/truenas-netboot/lib /opt/truenas-netboot/curl --fail --location --retry 3 --connect-timeout 30 --cacert /opt/truenas-netboot/ca-certificates.crt --output "$3" "$1"
'''
    return [('opt', b'', 0o40755), ('opt/truenas-netboot', b'', 0o40755),
            ('opt/truenas-netboot/lib', b'', 0o40755),
            ('opt/truenas-netboot/curl', curl, 0o100755),
            ('opt/truenas-netboot/ca-certificates.crt',
             read('etc/ssl/certs/ca-certificates.crt'), 0o100644),
            *[('opt/truenas-netboot/lib/' + name, data, 0o100755)
              for name, data in sorted(dependencies.items())],
            ('opt/truenas-netboot/wget', wrapper, 0o100755),
            (mount_path, mount_script, 0o100755)]


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
                    'vmlinuz', 'initrd.img', 'boot/grub/grub.cfg', 'live/filesystem.squashfs'], check=True)
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
        stream.write(media_archive(HOOK.read_bytes().replace(b'\r\n', b'\n'), order,
                                   tls_downloader(extracted, seven_zip)))
    hashes = {}
    for path in sorted(output.glob('truenas-*')):
        with path.open('rb') as source:
            hashes[path.name] = hashlib.file_digest(source, 'sha256').hexdigest()
    (output / 'SHA256SUMS').write_text(''.join(f'{h}  {n}\n' for n, h in hashes.items()), encoding='ascii')
    (output / 'source.json').write_text(json.dumps({
        'version': VERSION, 'iso_url': ISO_URL, 'iso_sha256': digest,
        'assets_sha256': hashes,
        'modification': 'ISO curl with verified TLS and isolated libraries; init-bottom media bind hook',
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--iso', type=Path)
    parser.add_argument('--seven-zip', default='7z')
    args = parser.parse_args()
    prepare(args.output, args.iso, args.seven_zip)
