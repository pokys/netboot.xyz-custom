import re
import tempfile
import unittest
from pathlib import Path

from tools.prepare_truenas import media_archive, prepare, HOOK

ROOT = Path(__file__).resolve().parents[1]


class TrueNASInstallerTests(unittest.TestCase):
    def test_media_hook_is_executable_and_scheduled_after_existing_cleanup(self):
        original_order = b'/scripts/init-bottom/udev "$@"\n'
        script = HOOK.read_bytes().replace(b'\r\n', b'\n')
        data = media_archive(script, original_order)
        files = {}
        position = 0
        while True:
            self.assertEqual(data[position:position + 6], b'070701')
            fields = [int(data[i:i + 8], 16) for i in range(position + 6, position + 110, 8)]
            self.assertEqual(fields[2:4], [0, 0])
            name_start = position + 110
            name = data[name_start:name_start + fields[11] - 1].decode()
            start = (name_start + fields[11] + 3) & ~3
            content = data[start:start + fields[6]]
            if name == 'TRAILER!!!':
                break
            files[name] = (fields[1], content)
            position = (start + fields[6] + 3) & ~3
        self.assertEqual(files['scripts/init-bottom/truenas-netboot'], (0o100755, script))
        order = files['scripts/init-bottom/ORDER'][1]
        self.assertTrue(order.startswith(original_order))
        self.assertIn(b'/scripts/init-bottom/truenas-netboot "$@"', order)

    def test_corrupt_iso_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            iso = root / 'bad.iso'
            iso.write_bytes(b'not the official ISO')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                prepare(root / 'output', iso, seven_zip='must-not-be-called')
            self.assertFalse((root / 'output/truenas-vmlinuz').exists())

    def test_menu_uses_kernel_initrd_and_has_valid_targets(self):
        menu = (ROOT / 'truenas.ipxe').read_text()
        labels = re.findall(r'^:([\w_]+)$', menu, re.M)
        self.assertEqual(len(labels), len(set(labels)))
        for target in re.findall(r'^item ([\w_]+) ', menu, re.M) + re.findall(r'\bgoto ([a-zA-Z_][\w_]*)', menu):
            self.assertIn(target, labels)
        self.assertIn('fetch=${truenas_iso}', menu)
        self.assertIn('initrd --name truenas-initrd', menu)
        self.assertNotIn('sanboot', menu)
        self.assertNotIn('toram=', menu)  # ISO is already downloaded into RAM.


if __name__ == '__main__':
    unittest.main()
