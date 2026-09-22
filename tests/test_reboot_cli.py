import unittest
import sys
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "scripts"))

import importlib.machinery
import importlib.util

loader = importlib.machinery.SourceFileLoader("omarchy_boot", str(repo_root / "scripts" / "omarchy-boot"))
spec = importlib.util.spec_from_loader("omarchy_boot", loader)
omarchy_boot = importlib.util.module_from_spec(spec)
loader.exec_module(omarchy_boot)


class TestRebootCli(unittest.TestCase):
    def test_imports_and_globals(self):
        """Ensure all required standard library modules including 're' are available."""
        self.assertTrue(hasattr(omarchy_boot, "re"), "Module 're' must be imported in omarchy-boot")
        self.assertTrue(hasattr(omarchy_boot, "subprocess"))
        self.assertTrue(hasattr(omarchy_boot, "argparse"))

    def test_cmd_reboot_windows_dryrun(self):
        """Test cmd_reboot targets windows and invokes the runner with sanitized win_id."""
        fake_entries = {
            "current": "0003",
            "order": ["0003", "0000"],
            "entries": [{"id": "0000", "title": "Windows Boot Manager", "is_windows": True}],
            "windows_id": "0000",
        }
        fake_parts = [{"partuuid": "8a80c1ba-ee7f-4114-929e-cef5b92cf75e", "title": "Windows"}]

        captured_runner = []

        def fake_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and (cmd[0] in ("sudo", "pkexec") or (len(cmd) > 1 and cmd[1] == "-c")):
                captured_runner.append(cmd)
                m = MagicMock()
                m.returncode = 0
                return m
            m = MagicMock()
            m.returncode = 0
            m.stdout = ""
            return m

        with patch.object(omarchy_boot, "get_efi_boot_entries", return_value=fake_entries), \
             patch.object(omarchy_boot, "get_windows_partitions", return_value=fake_parts), \
             patch.object(omarchy_boot, "read_limine_config", return_value="efi_chainload bootmgfw.efi"), \
             patch.object(omarchy_boot.subprocess, "run", side_effect=fake_run):
            omarchy_boot.cmd_reboot(argparse.Namespace(target="windows"))

        self.assertTrue(len(captured_runner) > 0, "Elevated reboot runner must be called")
        last_call = captured_runner[-1]
        self.assertEqual(last_call[-1], "0000", "Sanitized Windows ID '0000' should be passed as argument")


if __name__ == "__main__":
    unittest.main()
