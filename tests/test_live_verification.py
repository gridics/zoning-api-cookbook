import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("verify_live", Path(__file__).resolve().parents[1] / "tools/verify_live.py")
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)


class LiveVerificationTests(unittest.TestCase):
    def test_workflow_forwards_every_recipe_fixture_variable(self):
        import re
        root = Path(__file__).resolve().parents[1]
        manifest = (root / "recipes/manifest.json").read_text()
        required = set(re.findall(r"\$\{(GRIDICS_[A-Z_]+)\}", manifest))
        workflow = (root / ".github/workflows/live-verification.yml").read_text()
        forwarded = set(re.findall(r"(GRIDICS_[A-Z_]+): \$\{\{ vars\.", workflow))
        self.assertEqual(required - forwarded, set())

    def test_location_search_is_selectable_for_bounded_verification(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/live-verification.yml").read_text()
        self.assertIn("'18'", workflow)
        self.assertIn("GRIDICS_LOCATION_QUERY: ${{ vars.GRIDICS_LOCATION_QUERY }}", workflow)

    def test_failure_metadata_retains_only_http_codes(self):
        raw = json.dumps({"results": [{"http_status": 403, "message": "private provider response", "data": "secret"},
                                     {"http_status": "secret"}]})
        self.assertEqual(live.failure_metadata(raw, "03"), {"recipe": "03", "result_status": "failed", "http_statuses": [403]})

    def test_only_selected_recipe_inputs_are_required(self):
        discovery = {"steps": [{"path": "/v2/markets/${GRIDICS_MARKET_ID}/places"}]}
        self.assertEqual(live.missing_fixture_variables(discovery, {"GRIDICS_MARKET_ID": "fixture-market"}), [])
        self.assertEqual(live.missing_fixture_variables(discovery, {}), ["GRIDICS_MARKET_ID"])
        lookup = {"steps": [{"body": {"address": {"postal_code": "${GRIDICS_POSTAL_CODE}"}}}]}
        self.assertEqual(live.missing_fixture_variables(lookup, {}), ["GRIDICS_POSTAL_CODE"])

    def environment(self):
        return {"GRIDICS_API_KEY": "fixture-secret-never-retained", "GRIDICS_API_BASE_URL": "https://api.gridics.com", "GRIDICS_VERIFICATION_PROFILE": "public-cookbook-test"}

    def payload(self):
        return {"recipe": "01", "execution": "live", "status": "ok", "request_count": 1,
                "results": [{"status": "ok", "http_status": 200, "data": {"private_fixture": "must not be retained"}}]}

    def test_only_production_public_origin_is_accepted(self):
        live.validate_environment(self.environment())
        for field, value in [
            ("GRIDICS_API_KEY", ""),
            ("GRIDICS_VERIFICATION_PROFILE", "default"),
            ("GRIDICS_API_BASE_URL", "http://api.gridics.com"),
            ("GRIDICS_API_BASE_URL", "https://api.gridics.com.attacker.test"),
            ("GRIDICS_API_BASE_URL", "https://api.gridics.com/path"),
        ]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                live.validate_environment({**self.environment(), field: value})

    def test_retained_evidence_contains_no_response_data(self):
        evidence = live.summarize(self.payload(), "01", self.environment()["GRIDICS_API_KEY"])
        self.assertEqual(evidence["result_status"], "verified")
        self.assertNotIn("private_fixture", json.dumps(evidence))

    def test_fixture_and_unbounded_results_are_not_live_acceptance(self):
        for field, value in [("execution", "fixture"), ("execution", "dry_run"), ("request_count", 99), ("status", "error")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                live.summarize({**self.payload(), field: value}, "01", self.environment()["GRIDICS_API_KEY"])

    def test_unavailable_capability_is_explicitly_not_verified(self):
        payload = self.payload()
        payload["results"][0]["status"] = "unavailable"
        evidence = live.summarize(payload, "01", self.environment()["GRIDICS_API_KEY"])
        self.assertEqual(evidence["result_status"], "capability_unavailable")

    def test_location_receipt_requires_resolved_matching_property(self):
        payload = {**self.payload(), "recipe": "18", "workflow": {"state": "resolved", "features": [{"properties": {"parcel_id": "fixture-parcel"}}]}}
        self.assertEqual(live.summarize(payload, "18", "fixture-secret", "fixture-parcel")["result_status"], "verified")
        for workflow in [{"state": "no_match", "features": []}, {"state": "resolved", "features": []}, {"state": "ambiguous", "features": [{"properties": {"parcel_id": "fixture-parcel"}}]}, {"state": "resolved", "features": [{"properties": {"parcel_id": "other-fixture"}}]}]:
            with self.subTest(workflow=workflow), self.assertRaises(ValueError):
                live.summarize({**payload, "workflow": workflow}, "18", "fixture-secret", "fixture-parcel")

    def test_secret_in_response_is_rejected_without_echoing_it(self):
        payload = self.payload()
        payload["results"][0]["data"] = self.environment()["GRIDICS_API_KEY"]
        with self.assertRaises(ValueError) as error:
            live.summarize(payload, "01", self.environment()["GRIDICS_API_KEY"])
        self.assertNotIn(self.environment()["GRIDICS_API_KEY"], str(error.exception))


if __name__ == "__main__":
    unittest.main()
