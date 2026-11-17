"""Backwards-compatibility tests after Chat -> fixed terminal cutover.

The adapter retains this import name because the GitHub checker uses it, but
its public prepare/send API now targets a pinned OpenCode TUI, never Chat.
"""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orca_existing_chat as fixed


class LegacyImportCompatibility(unittest.TestCase):
    def test_fixed_mode_selected(self):
        self.assertEqual(fixed.PIN_NAME, "opencode-fixed-terminal-binding.json")

    def test_not_found_blocks_without_launch(self):
        with tempfile.TemporaryDirectory() as d:
            repo=Path(d)
            with mock.patch.object(fixed, "_pin", return_value=repo/"binding.json"), \
                 mock.patch.object(fixed, "_run", return_value={"terminals": []}) as cli:
                with self.assertRaisesRegex(fixed.ChatUnavailable,"NOT_FOUND"):
                    fixed.prepare(repo, repo)
                self.assertEqual(cli.call_args.args[1][:2], ["terminal", "list"])

    def test_unconfirmed_result_does_not_claim_success(self):
        with tempfile.TemporaryDirectory() as d:
            repo=Path(d)
            with mock.patch.object(fixed,"_pin",return_value=repo/"binding.json"):
                with self.assertRaises(fixed.ChatDeliveryUnconfirmed):
                    fixed.send(repo, {"session_id":"term_missing","workspace":str(repo)}, "继续")


if __name__ == "__main__":
    unittest.main()
