from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orca_existing_chat as fixed


class FixedTerminalTests(unittest.TestCase):
    def test_normalizes_slashes(self):
        self.assertEqual(fixed._norm("D:/X/Y"), fixed._norm(r"D:\X\Y") if sys.platform=="win32" else fixed._norm("D:/X/Y"))

    def test_missing_terminal_refuses_to_create(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp)
            with patch.object(fixed,"_pin",return_value=repo/"pin.json"),\
                 patch.object(fixed,"_run",return_value={"terminals":[]}),\
                 patch.object(fixed,"_gitdir",return_value=repo):
                with self.assertRaisesRegex(fixed.ChatUnavailable,"NOT_FOUND"):
                    fixed.prepare(repo,repo)

    def test_pins_only_one_verified_terminal_and_reuses(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp)
            term={"handle":"term_one","worktreePath":str(repo),"incarnationId":"inc_1",
                  "agentIdentity":"opencode","connected":True,"writable":True,"orphaned":False}
            def cli(_repo,args,**kw):
                if args[1]=="list": return {"terminals":[term]}
                if args[1]=="show": return {"terminal":term}
                if args[1]=="wait": return {"wait":{"satisfied":True}}
                raise AssertionError(args)
            with patch.object(fixed,"_pin",return_value=repo/"pin.json"),\
                 patch.object(fixed,"_run",side_effect=cli):
                first=fixed.prepare(repo,repo)
                again=fixed.prepare(repo,repo)
                self.assertEqual(first["terminal_handle"],"term_one")
                self.assertEqual(again["terminal_handle"],"term_one")
                saved=json.loads((repo/"pin.json").read_text())
                self.assertEqual(saved["incarnation_id"],"inc_1")

    def test_changed_incarnation_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp)
            (repo/"pin.json").write_text(json.dumps({"handle":"term_one",
                "incarnation_id":"old","workspace":str(repo)}))
            term={"handle":"term_one","worktreePath":str(repo),"incarnationId":"new",
                  "agentIdentity":"opencode","connected":True,"writable":True,"orphaned":False}
            with patch.object(fixed,"_pin",return_value=repo/"pin.json"),\
                 patch.object(fixed,"_run",return_value={"terminal":term}):
                with self.assertRaisesRegex(fixed.ChatUnavailable,"CHANGED"):
                    fixed.prepare(repo,repo)

    def test_send_only_to_pinned_same_handle(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp)
            (repo/"pin.json").write_text(json.dumps({"handle":"term_correct","incarnation_id":"i",
                                                     "workspace":str(repo)}))
            with patch.object(fixed,"_pin",return_value=repo/"pin.json"),\
                 patch.object(fixed,"_run") as cli:
                with self.assertRaisesRegex(fixed.ChatDeliveryUnconfirmed,"HANDLE_CHANGED"):
                    fixed.send(repo,{"session_id":"term_wrong","workspace":str(repo)},"继续")
                cli.assert_not_called()

    def test_send_accepted_no_new_window(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp)
            (repo/"pin.json").write_text(json.dumps({"handle":"term_ok","incarnation_id":"i",
                                                     "workspace":str(repo)}))
            term={"handle":"term_ok","worktreePath":str(repo),"incarnationId":"i",
                  "agentIdentity":"opencode","connected":True,"writable":True,"orphaned":False}
            def cli(_repo,args,**kw):
                if args[1]=="show": return {"terminal":term}
                if args[1]=="send":
                    self.assertNotIn("launch",args)
                    self.assertIn("--enter",args)
                    return {"send":{"accepted":True}}
                raise AssertionError(args)
            with patch.object(fixed,"_pin",return_value=repo/"pin.json"),\
                 patch.object(fixed,"_run",side_effect=cli):
                self.assertTrue(fixed.send(repo,{"session_id":"term_ok","workspace":str(repo)},"继续")["accepted"])


if __name__ == "__main__":
    unittest.main()
