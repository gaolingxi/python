from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import orca_existing_chat as c


class ExistingChatTests(unittest.TestCase):
    def sample(self, state="done"):
        return {"chats":[
            {"sessionId":"existing_chat_s1","agentType":"opencode",
             "state":state,"updatedAt":"2026-11-17T12:00:00Z"},
            {"sessionId":"old_chat_s0","agentType":"opencode",
             "state":"done","updatedAt":"2026-11-16T12:00:00Z"},
        ]}

    def test_old_orca_does_not_attempt_send(self):
        with tempfile.TemporaryDirectory() as t:
            with mock.patch.object(c,"supported",return_value=False),\
                 mock.patch.object(c,"_run") as api:
                with self.assertRaisesRegex(c.ChatUnavailable,"WAIT_ORCA_VERSION"):
                    c.prepare(Path(t),Path(t))
                api.assert_not_called()

    def test_one_existing_chat_is_pinned_and_reused(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);workspace=Path(t)/"worktree";workspace.mkdir()
            pin=repo/"pin.json"
            with mock.patch.object(c,"supported",return_value=True),\
                 mock.patch.object(c,"_pin",return_value=pin),\
                 mock.patch.object(c,"_run",side_effect=[self.sample(),
                                 {"status":"submitted"}, self.sample()]) as api:
                first=c.prepare(repo,workspace)
                self.assertEqual(first["session_id"],"existing_chat_s1")
                result=c.send(repo,first,"继续 T2")
                self.assertEqual(result["session_id"],"existing_chat_s1")
                self.assertEqual(result["chat_admission"],"submitted")
                second=c.prepare(repo,workspace)
                self.assertEqual(second["session_id"],first["session_id"])
            self.assertEqual(json.loads(pin.read_text())["session_id"],"existing_chat_s1")
            calls=[x.args[1] for x in api.call_args_list]
            self.assertEqual(calls[0][:2],["chat","list"])
            self.assertEqual(calls[1][:2],["chat","send"])
            self.assertEqual(calls[1][calls[1].index("--session")+1],"existing_chat_s1")
            self.assertFalse(any("launch" in argv for args in calls for argv in args))

    def test_wait_if_pinned_session_not_present(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);workspace=repo/"w";workspace.mkdir()
            pin=repo/"pin.json"
            pin.write_text(json.dumps({"session_id":"gone","workspace":str(workspace.resolve())}))
            with mock.patch.object(c,"supported",return_value=True),\
                 mock.patch.object(c,"_pin",return_value=pin),\
                 mock.patch.object(c,"_run",return_value=self.sample()):
                with self.assertRaisesRegex(c.ChatUnavailable,"PINNED_CHAT_MISSING"):
                    c.prepare(repo,workspace)

    def test_wait_if_chat_is_working(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);workspace=repo/"w";workspace.mkdir()
            with mock.patch.object(c,"supported",return_value=True),\
                 mock.patch.object(c,"_pin",return_value=repo/"missing.json"),\
                 mock.patch.object(c,"_run",return_value=self.sample("working")):
                with self.assertRaisesRegex(c.ChatUnavailable,"NOT_IDLE"):
                    c.prepare(repo,workspace)

    def test_unconfirmed_chat_ack_never_fakes_success(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t)
            target={"session_id":"existing_chat_s1","workspace":str(repo)}
            with mock.patch.object(c,"supported",return_value=True),\
                 mock.patch.object(c,"_pin",return_value=repo/"pin.json"),\
                 mock.patch.object(c,"_run",return_value={"unknown":"response"}):
                with self.assertRaises(c.ChatDeliveryUnconfirmed):
                    c.send(repo,target,"继续")


if __name__=="__main__":
    unittest.main()
