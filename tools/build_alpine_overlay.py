"""Build the public, credential-free Alpine Docker Live configuration archive."""
import argparse
import gzip
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'alpine' / 'overlay'
OUTPUT = ROOT / 'alpine' / 'docker-live.apkovl.tar.gz'
SERVICES = {
    'sysinit': ('devfs', 'dmesg', 'mdev', 'hwdrivers', 'modloop'),
    'boot': ('modules', 'sysctl', 'hostname', 'bootmisc', 'syslog', 'networking', 'cgroups'),
    'default': ('live-access', 'sshd', 'docker', 'dockge-live'),
    'shutdown': ('mount-ro', 'killprocs'),
}


def build():
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for path in sorted(SOURCE.rglob('*')):
            if not path.is_file():
                continue
            name = path.relative_to(SOURCE).as_posix()
            data = path.read_bytes().replace(b'\r\n', b'\n')
            info = tarfile.TarInfo(name)
            info.mode = 0o755 if name.startswith(('etc/init.d/', 'usr/local/sbin/')) else 0o644
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        for runlevel, services in SERVICES.items():
            for service in services:
                info = tarfile.TarInfo(f'etc/runlevels/{runlevel}/{service}')
                info.type = tarfile.SYMTYPE
                info.linkname = '/etc/init.d/' + service
                info.mode = 0o777
                archive.addfile(info)
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode='wb', filename='', mtime=0) as compressed:
        compressed.write(raw.getvalue())
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = build()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != data:
            raise SystemExit('Alpine overlay archive is stale; run tools/build_alpine_overlay.py')
    else:
        OUTPUT.write_bytes(data)
    print(f'Alpine Docker Live overlay: {len(data)} bytes; no saved credentials')


if __name__ == '__main__':
    main()
