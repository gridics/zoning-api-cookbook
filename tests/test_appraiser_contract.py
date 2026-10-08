import copy
import unittest
from run_appraiser_parity import CASES, verify_report


class AppraiserContract(unittest.TestCase):
    def test_complete_case_matrix(self):
        self.assertEqual({c['name'] for c in CASES},{'address','apn','parcel','not_found','ambiguous','wrong_county','zoning_unavailable','partial','quota'})
        partial=next(c for c in CASES if c['name']=='partial')['expected_report']
        self.assertIsNone(partial['property']['fields']['parcel.lot_area'])
        self.assertNotIn('setbacks',partial['unknowns'])  # Returned zero is a fact, not missing.
        self.assertIn('height',partial['unknowns'])

    def test_apn_null_precision_and_provenance_mismatches_fail(self):
        expected=CASES[0]['expected_report']
        for mutate in [
            lambda r:r['property']['identifiers'].update(apn='141140060030'),
            lambda r:r['property']['fields'].update({'parcel.lot_area':7500.1}),
            lambda r:r.update(zoning=None),
            lambda r:r['provenance'][0].update(request_id='incorrect-request'),
        ]:
            report=copy.deepcopy(expected);report['retrieved_at']='2026-10-02T00:00:00Z';mutate(report)
            with self.assertRaises(AssertionError):verify_report(report,expected)
