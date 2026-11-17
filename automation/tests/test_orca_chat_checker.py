from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orca_chat_checker as w


def snap(task="NEW", status="PENDING", ready="YES"):
    return {
        "task_id": task, "status": status,
        "executor": "OPENCODE", "next_actor": "OPENCODE",
        "automation_ready": ready, "user_review_required": "NO",
        "report_task_id": "", "report_status": "",
        "task_blob": "blob1", "remote_head": "head1",
    }


class ChatCheckerTests(unittest.TestCase):
    def wrap(self, repo, task):
        return (mock.patch.object(w, "snapshot", return_value=task),
                mock.patch.object(w, "runtime_dir", return_value=repo / ".git" / "checker"))

    def test_requires_explicit_approval(self):
        self.assertEqual(w.decision(snap(ready="NO")), "IDLE_AUTOMATION_NOT_APPROVED")
        self.assertEqual(w.decision(snap(status="DONE")), "IDLE_NOT_READY")
        self.assertEqual(w.decision(snap(task="NONE")), "IDLE_NO_TASK")

    def test_first_tick_baselines_instead_of_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = self.wrap(root, snap())
            with a, b, mock.patch.object(w, "launch_chat") as launch:
                self.assertEqual(w.check_once(root)["status"], "BASELINE_SET_NO_EXECUTION")
                self.assertEqual(w.check_once(root)["status"], "BASELINE_TASK_SKIPPED")
                launch.assert_not_called()

    def test_new_task_launches_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = self.wrap(root, snap())
            with a, b, mock.patch.object(w, "registered_workspace"), \
                 mock.patch.object(w, "prepare_chat", return_value={"session_id":"fixture","workspace":"fixture"}), \
                 mock.patch.object(w, "launch_chat", return_value={"chat_outcome": "chat"}) as launch:
                self.assertEqual(w.check_once(root)["status"], "BASELINE_SET_NO_EXECUTION")
                with mock.patch.object(w, "snapshot", return_value=snap("NEXT")):
                    self.assertEqual(w.check_once(root)["status"], "EXISTING_CHAT_MESSAGED")
                    self.assertEqual(w.check_once(root)["status"], "ALREADY_CLAIMED_OR_UNCONFIRMED")
                self.assertEqual(launch.call_count, 1)

    def test_uncertain_failure_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = self.wrap(root, snap())
            with a, b:
                w.check_once(root)
                with mock.patch.object(w, "snapshot", return_value=snap("NEXT")), \
                     mock.patch.object(w, "registered_workspace"), \
                     mock.patch.object(w, "prepare_chat", return_value={"session_id":"fixture","workspace":"fixture"}), \
                     mock.patch.object(w, "launch_chat", side_effect=RuntimeError("unconfirmed")) as launch:
                    with self.assertRaisesRegex(RuntimeError, "unconfirmed"):
                        w.check_once(root)
                    self.assertEqual(w.check_once(root)["status"], "ALREADY_CLAIMED_OR_UNCONFIRMED")
                    self.assertEqual(launch.call_count, 1)

    def test_doctor_is_non_launching(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a,b = self.wrap(root,snap())
            with a,b,mock.patch.object(w,"registered_workspace"),mock.patch.object(w,"launch_chat") as launch:
                self.assertEqual(w.check_once(root,doctor=True)["status"],"DOCTOR_READY")
                launch.assert_not_called()

    def test_existing_chat_sender_is_used_without_launch(self):
        target = {"session_id": "existing-session", "workspace": "D:/course/python"}
        with mock.patch.object(w, "send_chat",
                               return_value={"chat_outcome": "existing",
                                             "session_id": "existing-session",
                                             "chat_admission": "submitted"}) as send:
            result = w.launch_chat(Path("D:/course/python"), "T2", target)
        self.assertEqual(result["chat_outcome"], "existing")
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.args[1], target)


if __name__ == "__main__":
    unittest.main()
