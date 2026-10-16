"""Prepare pinned Puppy/Slax live boot assets from verified upstream ISOs.

Requires Python 3 and 7-Zip. Output is a new directory, ready for a GitHub Release.
No disk mounting, installation, credentials or release publishing is performed.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

MEDIA = {
    'puppy': {
        'iso': 'BookwormPup64_10.0.12.iso',
        'url': 'https://ftp.nluug.nl/os/Linux/distr/puppylinux/puppy-bookwormpup/BookwormPup64/10.0.12/BookwormPup64_10.0.12.iso',
        'algorithm': 'sha256',
        'digest': 'ae65f6e6d70a96f48bdbb291c2426f8a2fd77a73692e149e81a5eecb6fe7509f',
    },
    'slax': {
        'iso': 'slax-64bit-debian-12.2.0.iso',
        'url': 'https://ftp.sh.cvut.cz/slax/Slax-Debian-12.x/slax-64bit-debian-12.2.0.iso',
        'algorithm': 'md5',  # Upstream publishes only MD5; not an authenticity check.
        'digest': '96369071b0eeed78f6bb64b8148cbb34',
    },
}


def append_cpio(stream, paths):
    """Append a Linux newc initramfs archive containing regular root-level files."""
    stream.write(b'\0' * (-stream.tell() % 4))
    for inode, path in enumerate([*paths, None], 1):
        name = (path.name if path else 'TRAILER!!!').encode('ascii') + b'\0'
        size = path.stat().st_size if path else 0
        mode = (0o100755 if path.name == 'init' else 0o100644) if path else 0
        fields = [inode, mode, 0, 0, 1, 0, size, 0, 0, 0, 0, len(name), 0]
        header = b'070701' + ''.join(f'{value:08x}' for value in fields).encode('ascii')
        stream.write(header + name)
        stream.write(b'\0' * (-(len(header) + len(name)) % 4))
        if path:
            with path.open('rb') as source:
                shutil.copyfileobj(source, stream)
        stream.write(b'\0' * (-size % 4))


def prepare(profile, output, iso=None, seven_zip='7z'):
    media = MEDIA[profile]
    output.mkdir(parents=True, exist_ok=False)
    if iso is None:
        iso = output / media['iso']
        urllib.request.urlretrieve(media['url'], iso)
    with iso.open('rb') as source:
        digest = hashlib.file_digest(source, media['algorithm']).hexdigest()
    if digest != media['digest']:
        raise ValueError('ISO checksum mismatch; extraction refused')
    extracted = output / 'extracted'
    patterns = ['vmlinuz', 'initrd.gz', '*.sfs'] if profile == 'puppy' else ['slax/boot/vmlinuz', 'slax/boot/initrfs.img']
    subprocess.run([seven_zip, 'x', '-y', '-o' + str(extracted), str(iso), *patterns], check=True)
    if profile == 'puppy':
        sfs = sorted(extracted.glob('*.sfs'))
        if not any(path.name.startswith('puppy_') for path in sfs):
            raise ValueError('Puppy main SFS is missing')
        shutil.copyfile(extracted / 'vmlinuz', output / 'puppy-vmlinuz')
        # This release moves the embedded main SFS to /mnt/tmpfs before checking
        # its original path. Accept the moved file as stack_onepupdrv already does.
        unpacked = output / 'original-initrd'
        subprocess.run([seven_zip, 'x', '-y', '-o' + str(unpacked), str(extracted / 'initrd.gz')], check=True)
        subprocess.run([seven_zip, 'e', '-y', '-o' + str(unpacked), str(unpacked / 'initrd'), 'init'], check=True)
        init = unpacked / 'init'
        source = init.read_bytes()
        old = b'if ! [ -s "$ONE_FN" ] ; then'
        new = b'if ! [ -s "$ONE_FN" ] && ! [ -s "/mnt/tmpfs/$ONE_BASENAME" ]; then'
        if source.count(old) != 1:
            raise ValueError('Unexpected Puppy init; review the embedded SFS compatibility fix')
        init.write_bytes(source.replace(old, new))
        target = output / 'puppy-initrd'
        shutil.copyfile(extracted / 'initrd.gz', target)
        with target.open('ab') as stream:
            append_cpio(stream, [init, *sfs])
    else:
        for source, target in [('vmlinuz', 'slax-vmlinuz'), ('initrfs.img', 'slax-initrfs.img')]:
            shutil.copyfile(extracted / 'slax' / 'boot' / source, output / target)
    files = sorted(path for path in output.glob(profile + '-*') if path.is_file())
    hashes = {}
    for path in files:
        with path.open('rb') as source:
            hashes[path.name] = hashlib.file_digest(source, 'sha256').hexdigest()
    (output / 'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name, digest in hashes.items()), encoding='ascii')
    (output / 'source.json').write_text(json.dumps({'profile': profile, **media, 'assets_sha256': hashes}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', choices=MEDIA)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--iso', type=Path)
    parser.add_argument('--seven-zip', default='7z')
    args = parser.parse_args()
    prepare(args.profile, args.output, args.iso, args.seven_zip)
