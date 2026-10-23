import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("abutting_example", ROOT / "main.py")
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


class ExampleTests(unittest.TestCase):
    def test_fixture_retains_zoning_states_and_identity_directions(self):
        result = example.summarize(json.loads((ROOT / "response.json").read_text()))
        self.assertEqual(result["parcel_id"], "subject_example")
        self.assertEqual([row["direction"] for row in result["abutting"]], ["N", "E"])
        self.assertEqual(result["abutting"][1]["zoning_state"], "no_records")

    def test_missing_directions_and_empty_adjacency(self):
        payload = json.loads((ROOT / "response.json").read_text())
        payload["data"]["abutting"][0]["identity"].update(
            centroid=None, direction=None, bearing_degrees=None, direction_state="not_available"
        )
        self.assertIsNone(example.summarize(payload)["abutting"][0]["direction"])
        payload["data"]["abutting"] = []
        payload["meta"]["resource_states"]["abutting"] = "no_records"
        self.assertEqual(example.summarize(payload)["abutting"], [])

    def test_request_encodes_ids_and_keeps_key_out_of_url(self):
        with patch.object(example, "urlopen") as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'{"data":{}}'
            example.fetch_abutting("https://api.gridics.com", "SYNTHETIC_KEY", "parcel/a", "county & b")
            request = open_url.call_args.args[0]
            self.assertIn("/parcel%2Fa/abutting?place_id=county+%26+b", request.full_url)
            self.assertNotIn("SYNTHETIC_KEY", request.full_url)
            self.assertEqual(request.get_header("X-api-key"), "SYNTHETIC_KEY")
            self.assertEqual(open_url.call_args.kwargs["timeout"], 30)

    def test_insecure_origins_rejected_before_request(self):
        with self.assertRaises(ValueError):
            example.fetch_abutting("http://api.gridics.com", "SYNTHETIC_KEY", "parcel", "county")


if __name__ == "__main__":
    unittest.main()
