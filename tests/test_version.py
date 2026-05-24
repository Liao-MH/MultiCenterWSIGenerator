import unittest
import re
from pathlib import Path

from he_wsi_generator.constants import PACKAGE_VERSION, PROJECT_VERSION


class VersionTests(unittest.TestCase):
    def test_version_file_matches_package_version(self):
        repo_root = Path(__file__).resolve().parents[1]
        version_file = (repo_root / "VERSION").read_text(encoding="utf-8").strip()

        self.assertEqual(version_file, PROJECT_VERSION)
        self.assertEqual(PROJECT_VERSION, "v0.71.0")

    def test_pyproject_version_matches_project_version_without_v_prefix(self):
        repo_root = Path(__file__).resolve().parents[1]
        pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)

        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), PROJECT_VERSION.removeprefix("v"))
        self.assertEqual(match.group(1), PACKAGE_VERSION)


if __name__ == "__main__":
    unittest.main()
