import unittest
from validate_records import load, validate


class AuthorityRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.record, self.reconciliation = load()

    def test_supplied_approval_is_registered_without_acceptance(self):
        self.assertEqual(validate(self.record, self.reconciliation)["status"], "PASS")

    def test_wrong_option_is_rejected(self):
        self.record["selected_option"] = "B"
        with self.assertRaises(ValueError):
            validate(self.record, self.reconciliation)

    def test_fabricated_original_url_is_rejected(self):
        self.record["original_source"]["repository_url"] = "https://example.invalid/fake"
        with self.assertRaises(ValueError):
            validate(self.record, self.reconciliation)

    def test_release_promotion_is_rejected(self):
        self.record["gates"] = {**self.record["gates"], "PRODUCTION_RELEASE": "GO"}
        with self.assertRaises(ValueError):
            validate(self.record, self.reconciliation)

    def test_invented_journey_definition_is_rejected(self):
        self.reconciliation["journeys"][0]["description"] = "Invented journey"
        with self.assertRaises(ValueError):
            validate(self.record, self.reconciliation)

    def test_missing_traceability_is_rejected(self):
        del self.reconciliation["journeys"][0]["owner_uat_acceptance"]
        with self.assertRaises(ValueError):
            validate(self.record, self.reconciliation)

    def test_uat_acceptance_from_authority_is_rejected(self):
        self.reconciliation["closure_steps"][0]["owner_uat_acceptance"]["status"] = "ACCEPTED"
        with self.assertRaises(ValueError):
            validate(self.record, self.reconciliation)

    def test_original_closure_selections_are_preserved(self):
        self.record["preserved_decisions"][0]["selected_option"] = "A"
        with self.assertRaises(ValueError):
            validate(self.record, self.reconciliation)

    def test_no_automatic_later_step_completion(self):
        self.reconciliation["closure_steps"][1]["checklist_status"] = "VERIFIED_COMPLETE"
        with self.assertRaises(ValueError):
            validate(self.record, self.reconciliation)
