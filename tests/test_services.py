"""Services policy fixtures. No production service is changed."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "skills/services"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location("services_skill", DIRECTORY / "skill.py")
skill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skill)
from collector import eligible, state

BOOT = "11111111-1111-4111-8111-111111111111"
DEFAULTS = json.loads((DIRECTORY / "skill.json").read_text())["defaults"]


def advance(rows, previous=None, at=1800000000000, epochs=None, **settings):
    context = {"settings": {**DEFAULTS, "monitored_services": list(rows), **settings},
               "observation": {"boot_id": BOOT, "uptime_ms": 600000, "rows": [
                   {"key": key, "raw": raw, "result": "", "exit_status": "0"} for key, raw in rows.items()]},
               "previous_state": previous, "captured_at": at, "now": at,
               "resource_epochs": {"services": epochs or {key: "epoch-" + key for key in rows}},
               "evaluation_revision": "scalars-v1"}
    context["state"] = skill.reduce(context)
    return context, skill.evaluate(context)[0]["subjects"]


class ServicesTests(unittest.TestCase):
    def test_initial_stop_confirmation_and_recovery(self):
        first, subjects = advance({"a.service": "stopped"})
        self.assertEqual(subjects[0]["status"], "unknown")
        second, subjects = advance({"a.service": "failed"}, first["state"], at=first["now"] + 60000)
        self.assertEqual(subjects[0]["status"], "critical")
        self.assertEqual(second["state"]["rows"][0]["first_bad_at"], first["now"])
        _, subjects = advance({"a.service": "running"}, second["state"], at=second["now"] + 60000)
        self.assertEqual(subjects[0]["status"], "healthy")

    def test_distinct_observations_boot_gap_and_epoch(self):
        first, _ = advance({"a.service": "stopped"})
        for at, epochs in [(first["now"], None), (first["now"] - 1, None),
                           (first["now"] + 181000, None), (first["now"] + 60000, {"a.service": "new"})]:
            _, subjects = advance({"a.service": "stopped"}, first["state"], at=at, epochs=epochs)
            self.assertEqual(subjects[0]["status"], "unknown")
        before = {**first["state"], "boot_id": "22222222-2222-4222-8222-222222222222"}
        _, subjects = advance({"a.service": "stopped"}, before, at=first["now"] + 60000)
        self.assertEqual(subjects[0]["status"], "unknown")

    def test_startup_does_not_claim_healthy_and_clock_does_not_confirm(self):
        ctx, _ = advance({"a.service": "stopped"}, alert_after_seconds=0)
        ctx["observation"]["uptime_ms"] = 1000
        ctx["state"] = skill.reduce(ctx)
        ctx["now"] += 600000
        self.assertEqual(skill.evaluate(ctx)[0]["subjects"][0]["status"], "unknown")
        _, subjects = advance({"a.service": "missing"}, alert_after_seconds=0)
        self.assertEqual(subjects[0]["status"], "critical")

    def test_unrelated_target_and_independent_states(self):
        ctx, _ = advance({"a.service": "stopped"})
        ctx, subjects = advance({"a.service": "stopped", "b.service": "running"}, ctx["state"], at=ctx["now"] + 60000)
        self.assertEqual([r["status"] for r in subjects], ["critical", "healthy"])
        ctx, subjects = advance({"a.service": "unknown", "b.service": "running"}, ctx["state"], at=ctx["now"] + 60000)
        self.assertEqual([r["status"] for r in subjects], ["unknown", "healthy"])
        _, subjects = advance({"a.service": "stopped", "b.service": "reloading"}, ctx["state"], at=ctx["now"] + 60000)
        self.assertEqual([r["status"] for r in subjects], ["unknown", "healthy"])

    def test_classifier_handles_types_missing_and_alias_identity(self):
        p = {"Id": "a.service", "LoadState": "loaded", "ActiveState": "active", "SubState": "running",
             "Type": "simple", "RemainAfterExit": "no", "TriggeredBy": ""}
        item = {"available": True, "requested": "a.service", "reason": None, "properties": p}
        self.assertTrue(eligible(item)); self.assertEqual(state(item), "running")
        for changes in [{"Type": "oneshot"}, {"RemainAfterExit": "yes"}, {"TriggeredBy": "a.socket"}, {"Id": "a@.service"}]:
            self.assertFalse(eligible({**item, "properties": {**p, **changes}}))
        for load, raw in [("not-found", "missing"), ("masked", "masked"), ("bad-setting", "invalid")]:
            self.assertEqual(state({**item, "properties": {**p, "LoadState": load, "Type": ""}}), raw)
        self.assertEqual(state({**item, "properties": {**p, "Id": "other.service"}}), "review")
        self.assertEqual(state({"available": False, "reason": "unreadable"}), "unknown")

    def test_maximum_targets_and_empty_selection(self):
        _, subjects = advance({f"a-{i}.service": "running" for i in range(64)})
        self.assertEqual(len(subjects), 64)
        _, subjects = advance({})
        self.assertEqual(subjects, [])

    def test_large_discovery_is_partial_without_losing_selected_evidence(self):
        calls = []
        class Host:
            def request(self, operation, args):
                calls.append(operation)
                common = {"boot_id": BOOT, "uptime_ms": 600000}
                if operation.endswith("read"):
                    return {**common, "items": [{"requested": "a.service", "available": False, "reason": "unreadable", "properties": {}}]}
                return {**common, "complete": True, "reason": None, "items": [
                    {"requested": "x" * 230 + str(i) + "@.service", "available": False, "reason": "template", "properties": {}} for i in range(512)]}
        result = skill.collect({**DEFAULTS, "monitored_services": ["a.service"]}, Host())
        self.assertEqual(calls, ["systemd.services.read", "systemd.services.list"])
        self.assertEqual(result["observation"]["rows"][0]["raw"], "unknown")
        self.assertFalse(result["resources"][0]["complete"])
        self.assertLess(len(json.dumps(result["resources"],separators=(",", ":")).encode()), 262144)


if __name__ == "__main__":
    unittest.main()
