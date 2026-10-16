import io
import tempfile
import unittest
from pathlib import Path

from tools.prepare_small_live import append_cpio


class InitramfsArchiveTest(unittest.TestCase):
    def test_appended_archive_preserves_file_contents_and_root_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / 'init', Path(directory) / 'puppy_test.sfs']
            paths[0].write_bytes(b'#!/bin/sh\n')
            paths[1].write_bytes(b'hsqs\x00\xffdata')
            stream = io.BytesIO(b'original-gzip-data')
            stream.seek(0, 2)
            append_cpio(stream, paths)
            data = stream.getvalue()
            position = 20  # next four-byte boundary after original data
            for path, mode in zip(paths, [0o100755, 0o100644]):
                self.assertEqual(data[position:position + 6], b'070701')
                fields = [int(data[i:i + 8], 16) for i in range(position + 6, position + 110, 8)]
                self.assertEqual(fields[1:4], [mode, 0, 0])
                name_start = position + 110
                self.assertEqual(data[name_start:name_start + fields[11]], path.name.encode() + b'\0')
                content_start = (name_start + fields[11] + 3) & ~3
                self.assertEqual(data[content_start:content_start + fields[6]], path.read_bytes())
                position = (content_start + fields[6] + 3) & ~3
            self.assertIn(b'TRAILER!!!\0', data[position:])


if __name__ == '__main__':
    unittest.main()
