import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('esxi_catalog', ROOT / 'tools' / 'esxi_catalog.py')
catalog_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_tool)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / 'catalog' / 'esxi.json').read_text(encoding='utf-8'))
        cls.menu = catalog_tool.render_menu(cls.catalog)
        cls.entries = catalog_tool.source_entries(cls.catalog)

    def test_all_published_dell_index_images_are_retained(self):
        audit = json.loads((ROOT / 'catalog' / 'dell-discovery.json').read_text(encoding='utf-8'))
        actual = {image['filename'].lower() for image in self.catalog['images'] if image['vendor'] == 'Dell'
                  and any('/published/Pages/' in source for source in image['sources'])}
        self.assertEqual(len(actual), audit['published_index_unique_filenames'])

    def test_catalog_validation(self):
        catalog_tool.validate(self.catalog)

    def test_dell_entries_use_official_download_hosts(self):
        for image in self.catalog['images']:
            if image['vendor'] == 'Dell' and image.get('source_type') != 'third-party':
                self.assertRegex(image['url'], r'^https://(?:downloads|dl)\.dell\.com/')

    def test_all_image_targets_and_literal_jumps_exist(self):
        labels = re.findall(r'^:([\w_]+)$', self.menu, re.M)
        self.assertEqual(len(labels), len(set(labels)))
        for image in self.entries:
            self.assertEqual(labels.count(image['target']), 1)
            self.assertEqual(len(re.findall(r'^item ' + image['target'] + r' ', self.menu, re.M)), 1)
        for target in re.findall(r'\bgoto ([a-zA-Z_][\w_]*)', self.menu):
            self.assertIn(target, labels)
        for target in re.findall(r'\bitem ([a-zA-Z_][\w_]*) ', self.menu):
            self.assertIn(target, labels)

    def test_pages_fit_console_and_boot_returns_to_selected_page(self):
        for block in self.menu.split('\n:'):
            self.assertLessEqual(len(re.findall(r'^item ', block, re.M)), catalog_tool.PAGE_SIZE + 4)
            if block.startswith('image_'):
                self.assertRegex(block, r'\nset esxi_return source_\w+_\d+\n')
                self.assertIn('\ngoto esxi_boot', block)

    def test_unconfirmed_downloads_are_marked(self):
        for image in self.entries:
            line = next(line for line in self.menu.splitlines() if line.startswith('item ' + image['target'] + ' '))
            self.assertEqual(line.endswith('[?]'), not catalog_tool.ready(image))

    def test_source_selection_boots_only_selected_url(self):
        for entry in self.entries:
            block = self.menu.split('\n:' + entry['target'] + '\n', 1)[1].split('\n:', 1)[0]
            self.assertIn('\nset esxi_url ' + entry['url'] + '\n', '\n' + block)
            self.assertIn('set esxi_return source_' + entry['source'] + '_', block)
            self.assertIn('set esxi_source ' + catalog_tool.SOURCES[entry['source']][0], block)
        self.assertNotIn('esxi_alternate', self.menu)
        self.assertIn('echo URL: ${esxi_url}', self.menu)

    def test_mirror_checks_are_not_inherited_from_primary(self):
        image = copy.deepcopy(self.catalog['images'][0])
        image['check'] = {'usable': True}
        image['alternate_urls'] = ['https://vmware.digiboy.ir/8.X/' + image['filename']]
        image.pop('alternate_checks', None)
        entries = catalog_tool.source_entries({'images': [image]})
        self.assertTrue(catalog_tool.ready(entries[0]))
        self.assertFalse(catalog_tool.ready(entries[1]))

    def test_injected_script_and_unofficial_dell_hosts_are_rejected(self):
        for field, value in [('label', 'image\nreboot'), ('url', 'https://example.com/test.iso'),
                             ('family', '8.0 ${menu}')]:
            modified = copy.deepcopy(self.catalog)
            modified['images'][0][field] = value
            with self.assertRaises(ValueError):
                catalog_tool.validate(modified)


if __name__ == '__main__':
    unittest.main()
