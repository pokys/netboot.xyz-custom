import importlib.util
import io
import json
import re
import tarfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('overlay_builder', ROOT / 'tools/build_alpine_overlay.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
APPS = {'nextcloud', 'copyparty', 'wastebin', 'semaphore', 'caddy', 'uptime-kuma', 'guacamole', 'it-tools'}


class ApplianceTests(unittest.TestCase):
    def test_all_requested_apps_are_packaged_without_secrets_or_port_collisions(self):
        lock = json.loads((ROOT / 'catalog/appliance-images.json').read_text())['images']
        with tarfile.open(fileobj=io.BytesIO(builder.build()), mode='r:gz') as archive:
            templates = [name for name in archive.getnames() if name.startswith('opt/live-apps/templates/')]
            self.assertEqual({Path(name).parent.name for name in templates}, APPS)
            ports = []
            for name in templates:
                text = archive.extractfile(name).read().decode()
                for image in re.findall(r'image: (\S+)', text):
                    self.assertIn(image, lock.values())
                    self.assertRegex(image, r'@sha256:[0-9a-f]{64}$')
                ports.extend(re.findall(r'"(\d+):\d+"', text))
                for forbidden in ('privileged:', 'network_mode:', '/var/run/docker.sock', '/dev/', '/mnt/', '/media/'):
                    self.assertNotIn(forbidden, text)
            self.assertEqual(len(ports), len(set(ports)))
            self.assertNotIn('5001', ports)  # Dockge keeps its existing endpoint.
            self.assertFalse(any(Path(name).name == '.env' for name in archive.getnames()))

    def test_private_backends_and_first_boot_initialization(self):
        templates = ROOT / 'alpine/overlay/opt/live-apps/templates'
        guac = (templates / 'guacamole/compose.yaml').read_text()
        self.assertNotIn('4822:4822', guac)
        self.assertNotIn('5432:5432', guac)
        self.assertIn('condition: service_healthy', guac)
        self.assertIn('10-guacamole.sql:ro', guac)
        wastebin = (templates / 'wastebin/compose.yaml').read_text()
        self.assertIn('condition: service_completed_successfully', wastebin)
        self.assertIn('10001:10001', wastebin)
        script = (ROOT / 'alpine/overlay/usr/local/sbin/live-apps').read_text()
        self.assertIn('basic_auth', script)
        self.assertIn('--postgresql', script)
        self.assertIn('password_salt=decode', script)
        self.assertIn('cat "$state/ssh-password"', script)
        self.assertIn('Unknown application:', script)
        self.assertIn('compose config --quiet && compose up -d && wait_ready', script)

    def test_picker_and_shared_network_flow(self):
        menu = (ROOT / 'alpine-apps.ipxe').read_text()
        labels = re.findall(r'^:([\w_]+)$', menu, re.M)
        self.assertEqual(len(labels), len(set(labels)))
        for target in re.findall(r'\bgoto ([\w_]+)', menu) + re.findall(r'^item (?!-)([\w_]+)', menu, re.M):
            self.assertIn(target, labels)
        for app in APPS:
            self.assertIn('apps_' + app.replace('-', '_'), labels)
            self.assertIn('${alpine_live_apps},' + app, menu)
        self.assertIn('clear alpine_live_apps', menu)
        self.assertIn('/alpine-docker.ipxe', menu)
        shared = (ROOT / 'alpine-docker.ipxe').read_text()
        self.assertIn('live_apps=${alpine_live_apps}', shared)
        self.assertIn('set alpine_live_apps none', shared)


if __name__ == '__main__':
    unittest.main()
