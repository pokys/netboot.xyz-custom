import importlib.util
import io
import re
import tarfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_alpine_overlay', ROOT / 'tools' / 'build_alpine_overlay.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class AlpineOverlayTests(unittest.TestCase):
    def test_archive_is_reproducible_current_and_has_root_ownership(self):
        data = builder.build()
        self.assertEqual(data, builder.build())
        self.assertEqual(data, builder.OUTPUT.read_bytes())
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            for member in archive:
                self.assertEqual((member.uid, member.gid, member.uname, member.gname, member.mtime),
                                 (0, 0, '', '', 0))
                self.assertNotIn('..', Path(member.name).parts)
                if member.name.startswith(('etc/init.d/', 'usr/local/sbin/')):
                    self.assertEqual(member.mode, 0o755)

    def test_boot_services_and_credentials_are_not_preseeded(self):
        with tarfile.open(fileobj=io.BytesIO(builder.build()), mode='r:gz') as archive:
            names = archive.getnames()
            for forbidden in ('etc/shadow', 'etc/passwd', 'etc/fstab', 'root/.ssh/authorized_keys'):
                self.assertNotIn(forbidden, names)
            for service in ('live-access', 'sshd', 'docker', 'dockge-live'):
                member = archive.getmember('etc/runlevels/default/' + service)
                self.assertTrue(member.issym())
                self.assertEqual(member.linkname, '/etc/init.d/' + service)
            self.assertIn('etc/runlevels/boot/cgroups', names)
            script = archive.extractfile('usr/local/sbin/live-access').read().decode()
            self.assertIn('openssl rand -hex 12', script)
            self.assertIn('| chpasswd', script)

    def test_menu_targets_and_diskless_boot_parameters(self):
        menu = (ROOT / 'alpine-docker.ipxe').read_text()
        labels = re.findall(r'^:([\w_]+)$', menu, re.M)
        self.assertEqual(len(labels), len(set(labels)))
        for target in re.findall(r'\bgoto ([a-zA-Z_][\w_]*)', menu) + re.findall(r'^item ([a-zA-Z_][\w_]*) ', menu, re.M):
            self.assertIn(target, labels)
        self.assertIn('iseq ${arch} x86_64', menu)
        self.assertIn('ip=dhcp', menu)
        self.assertIn('apkovl=${alpine_live_overlay}', menu)
        self.assertIn('rootflags=size=85%', menu)
        self.assertNotIn('root=/dev/', menu)
        self.assertNotIn('setup-disk', menu)


if __name__ == '__main__':
    unittest.main()
