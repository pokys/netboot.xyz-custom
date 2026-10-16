import importlib.util
import io
import re
import tarfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('overlay_builder', ROOT / 'tools' / 'build_alpine_overlay.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class TailcatOverlayTests(unittest.TestCase):
    def test_tailcat_archive_is_current_and_independent_of_docker(self):
        data = builder.build('tailcat')
        self.assertEqual(data, builder.build('tailcat'))
        self.assertEqual(data, builder.TAILCAT_OUTPUT.read_bytes())
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            names = archive.getnames()
            self.assertNotIn('etc/apk/repositories', names)
            self.assertNotIn('etc/shadow', names)
            self.assertNotIn('etc/runlevels/default/docker', names)
            self.assertNotIn('opt/dockge/compose.yaml', names)
            world = archive.extractfile('etc/apk/world').read().decode().splitlines()
            self.assertIn('curl', world)
            self.assertIn('libqrencode-tools', world)
            self.assertNotIn('docker', world)
            self.assertNotIn('openssh', world)
            for name in builder.SHARED_NETWORK_FILES:
                self.assertEqual(archive.extractfile(name).read(), (builder.SOURCE / name).read_bytes().replace(b'\r\n', b'\n'))
            for member in archive:
                self.assertEqual((member.uid, member.gid, member.uname, member.gname), (0, 0, '', ''))

    def test_interactive_console_and_verified_download(self):
        with tarfile.open(fileobj=io.BytesIO(builder.build('tailcat')), mode='r:gz') as archive:
            inittab = archive.extractfile('etc/inittab').read().decode()
            for console in ('tty1', 'ttyS0'):
                self.assertRegex(inittab, rf'(?m)^{console}::respawn:.*-l /usr/local/sbin/tailcat-console')
            launcher = archive.extractfile('usr/local/sbin/tailcat-console').read().decode()
            self.assertRegex(launcher, r'Tailcat-OneShot/[a-f0-9]{40}/Tailcat_OneShot.sh')
            self.assertRegex(launcher, r'(?m)^        [a-f0-9]{64} \\')
            self.assertLess(launcher.index('sha256sum -c -'), launcher.index('mv "$download"'))
            self.assertIn('/bin/sh /opt/tailcat/Tailcat_OneShot.sh', launcher)
            self.assertNotIn('exit-node', launcher)
            self.assertEqual(archive.getmember('usr/local/sbin/tailcat-console').mode, 0o755)

    def test_menu_branches_network_choices_and_targets(self):
        menu = (ROOT / 'alpine-tailcat.ipxe').read_text()
        labels = re.findall(r'^:([\w_]+)$', menu, re.M)
        self.assertEqual(len(labels), len(set(labels)))
        for target in re.findall(r'\bgoto ([a-zA-Z_][\w_]*)', menu) + re.findall(r'^item ([a-zA-Z_][\w_]*) ', menu, re.M):
            self.assertIn(target, labels)
        self.assertIn('set alpine_live_branch v3.24', menu)
        self.assertIn('set alpine_live_branch latest-stable', menu)
        self.assertIn('ip=dhcp', menu)
        self.assertIn('read alpine_static_ip:ipv4', menu)
        self.assertIn('/alpine/tailcat-live.apkovl.tar.gz', menu)
        self.assertNotIn('docker-live.apkovl.tar.gz', menu)


if __name__ == '__main__':
    unittest.main()
