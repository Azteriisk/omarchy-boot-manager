import unittest
import sys
from pathlib import Path

# Add scripts directory to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "scripts"))

from core.limine_manager import (
    validate_guid,
    validate_label,
    generate_windows_entry,
    inject_windows_entry,
    add_windows_to_limine,
    set_limine_oneshot,
)


class TestLimineSecurityValidation(unittest.TestCase):
    def test_valid_guid(self):
        self.assertEqual(
            validate_guid("8A80C1BA-EE7F-4114-929E-CEF5B92CF75E"),
            "8a80c1ba-ee7f-4114-929e-cef5b92cf75e"
        )
        self.assertEqual(
            validate_guid("  8a80c1ba-ee7f-4114-929e-cef5b92cf75e  "),
            "8a80c1ba-ee7f-4114-929e-cef5b92cf75e"
        )

    def test_invalid_guid_injection_rejected(self):
        bad_guids = [
            "8a80c1ba-ee7f-4114-929e-cef5b92cf75e; id",
            "8a80c1ba-ee7f-4114-929e-cef5b92cf75e\nLIMEOF",
            "8a80c1ba-ee7f-4114-929e",
            "{8a80c1ba-ee7f-4114-929e-cef5b92cf75e}",
            "not-a-guid",
            "",
            "../etc/passwd",
        ]
        for bad in bad_guids:
            with self.subTest(guid=bad):
                with self.assertRaises(ValueError):
                    validate_guid(bad)

    def test_valid_label(self):
        valid_labels = [
            "Windows 11",
            "Windows 10 Pro",
            "Windows-11_Custom.Entry",
            "Win11",
            "W",
        ]
        for lbl in valid_labels:
            with self.subTest(label=lbl):
                self.assertEqual(validate_label(lbl), lbl.strip())

    def test_invalid_label_breakout_rejected(self):
        bad_labels = [
            "Windows 11\nLIMEOF\nrm -rf /",
            "Windows 11\r\nLIMEOF",
            "Windows; reboot",
            "Windows `id`",
            "Windows $(id)",
            "Windows | sh",
            "Windows & whoami",
            "Windows < /etc/shadow",
            "Windows \" && echo pwned",
            "",
            "   ",
            "-Windows",  # must start with alphanumeric
            "_Windows",
            "A" * 65,    # exceeds 64 chars
        ]
        for bad in bad_labels:
            with self.subTest(label=bad):
                with self.assertRaises(ValueError):
                    validate_label(bad)

    def test_generate_windows_entry_safe(self):
        entry = generate_windows_entry("8a80c1ba-ee7f-4114-929e-cef5b92cf75e", "Windows 11")
        self.assertIn("/Windows 11", entry)
        self.assertIn("guid(8a80c1ba-ee7f-4114-929e-cef5b92cf75e)", entry)

        # Attempt breakout in generate_windows_entry
        with self.assertRaises(ValueError):
            generate_windows_entry("8a80c1ba-ee7f-4114-929e-cef5b92cf75e", "Windows\nLIMEOF")

    def test_add_windows_to_limine_rejects_before_elevation(self):
        ok, msg = add_windows_to_limine("invalid-guid", "Windows 11")
        self.assertFalse(ok)
        self.assertIn("Invalid canonical partition GUID", msg)

        ok, msg = add_windows_to_limine("8a80c1ba-ee7f-4114-929e-cef5b92cf75e", "Bad\nLabel")
        self.assertFalse(ok)
        self.assertIn("Invalid label", msg)

    def test_set_limine_oneshot_rejects_before_elevation(self):
        ok, msg = set_limine_oneshot("Bad\nLabel")
        self.assertFalse(ok)
        self.assertIn("Invalid label", msg)


    def test_helper_execution_safe(self):
        import subprocess, tempfile, os
        from core.limine_manager import LIMINE_APPEND_HELPER

        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "limine.conf"
            cfg.write_text("timeout: 5\n", encoding="utf-8")

            # Run helper
            env = os.environ.copy()
            env["_OMARCHY_BOOT_TEST_PATH"] = "1"

            res = subprocess.run(
                [sys.executable, "-c", LIMINE_APPEND_HELPER, str(cfg), "8a80c1ba-ee7f-4114-929e-cef5b92cf75e", "Windows 11"],
                capture_output=True, text=True, env=env
            )
            self.assertEqual(res.returncode, 0, f"Helper failed: {res.stderr}")
            self.assertIn("Windows entry added successfully", res.stdout)

            # Check config content
            content = cfg.read_text(encoding="utf-8")
            self.assertIn("/Windows 11", content)
            self.assertIn("guid(8a80c1ba-ee7f-4114-929e-cef5b92cf75e)", content)

            # Second run should detect duplicate
            res2 = subprocess.run(
                [sys.executable, "-c", LIMINE_APPEND_HELPER, str(cfg), "8a80c1ba-ee7f-4114-929e-cef5b92cf75e", "Windows 11"],
                capture_output=True, text=True, env=env
            )
            self.assertEqual(res2.returncode, 0)
            self.assertIn("Windows entry already exists", res2.stdout)

            # Test breakout rejection in helper
            res3 = subprocess.run(
                [sys.executable, "-c", LIMINE_APPEND_HELPER, str(cfg), "8a80c1ba-ee7f-4114-929e-cef5b92cf75e", "Windows 11\nLIMEOF"],
                capture_output=True, text=True, env=env
            )
            self.assertNotEqual(res3.returncode, 0)
            self.assertIn("Invalid label", res3.stderr)


if __name__ == "__main__":
    unittest.main()
