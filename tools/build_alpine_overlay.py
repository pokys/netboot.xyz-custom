"""Build public, credential-free Alpine live configuration archives."""
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
    'boot': ('modules', 'sysctl', 'hostname', 'bootmisc', 'syslog', 'live-network', 'networking', 'cgroups'),
    'default': ('live-access', 'sshd', 'docker', 'dockge-live'),
    'shutdown': ('mount-ro', 'killprocs'),
}
TAILCAT_SOURCE = ROOT / 'alpine' / 'tailcat-overlay'
TAILCAT_OUTPUT = ROOT / 'alpine' / 'tailcat-live.apkovl.tar.gz'
TAILCAT_SERVICES = {
    'sysinit': SERVICES['sysinit'],
    'boot': tuple(service for service in SERVICES['boot'] if service != 'cgroups'),
    'shutdown': SERVICES['shutdown'],
}
SHARED_NETWORK_FILES = ('etc/init.d/live-network', 'usr/local/sbin/live-network', 'etc/network/interfaces')


def build(profile='docker'):
    if profile not in ('docker', 'tailcat'):
        raise ValueError('Unknown Alpine profile')
    source = SOURCE if profile == 'docker' else TAILCAT_SOURCE
    services = SERVICES if profile == 'docker' else TAILCAT_SERVICES
    files = {path.relative_to(source).as_posix(): path for path in source.rglob('*') if path.is_file()}
    if profile == 'tailcat':
        files.update({name: SOURCE / name for name in SHARED_NETWORK_FILES})
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, path in sorted(files.items()):
            data = path.read_bytes().replace(b'\r\n', b'\n')
            info = tarfile.TarInfo(name)
            info.mode = 0o755 if name.startswith(('etc/init.d/', 'usr/local/sbin/')) else 0o644
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        for runlevel, runlevel_services in services.items():
            for service in runlevel_services:
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
    parser.add_argument('--profile', choices=('docker', 'tailcat'), default='docker')
    args = parser.parse_args()
    data = build(args.profile)
    output = OUTPUT if args.profile == 'docker' else TAILCAT_OUTPUT
    if args.check:
        if not output.exists() or output.read_bytes() != data:
            raise SystemExit(f'Alpine {args.profile} archive is stale; rebuild with --profile {args.profile}')
    else:
        output.write_bytes(data)
    print(f'Alpine {args.profile} overlay: {len(data)} bytes; no saved credentials')


if __name__ == '__main__':
    main()
