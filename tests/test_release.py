"""Offline checks for public asset and link inspection."""

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_release import asset_valid, markdown_targets


class ReleaseChecks(unittest.TestCase):
    def test_local_links_and_remote_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("[local](docs/guide.md) [remote](https://example.org)\n")
            self.assertEqual(list(markdown_targets(root / "README.md")), [root / "docs/guide.md"])

    def test_asset_header_and_size(self):
        with tempfile.TemporaryDirectory() as directory:
            gif = Path(directory) / "example.gif"
            gif.write_bytes(b"GIF89a" + b"0" * 20)
            self.assertTrue(asset_valid(gif))
            gif.write_bytes(b"not a GIF")
            self.assertFalse(asset_valid(gif))

    def test_browser_gif_size_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            gif = Path(directory) / "workbench.gif"
            gif.write_bytes(b"GIF89a" + b"0" * (6 * 1024 * 1024))
            self.assertTrue(asset_valid(gif))
            gif.write_bytes(b"GIF89a" + b"0" * (9 * 1024 * 1024))
            self.assertFalse(asset_valid(gif))


if __name__ == "__main__":
    unittest.main()
