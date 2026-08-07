import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SchedulingMobileAccessibilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = (ROOT / "static" / "css" / "pages" / "scheduling-stitch.css").read_text(
            encoding="utf-8"
        )

    def test_mobile_metadata_has_readable_type_floor(self):
        self.assertIn("/* Mobile accessibility contract for the active scheduling flow. */", self.css)
        self.assertIn(".scheduling-new-page .scheduler-week-day-label", self.css)
        self.assertIn("font-size: 14px;", self.css)

    def test_mobile_temporal_controls_keep_touch_targets(self):
        self.assertIn(".scheduling-new-page .scheduler-flow-page .scheduler-week-nav button", self.css)
        self.assertIn("min-width: 44px;", self.css)
        self.assertIn("min-height: 44px;", self.css)

    def test_wizard_actions_stay_reachable_on_mobile(self):
        self.assertIn(".scheduling-new-page .scheduler-side-wizard .scheduler-flow-actions", self.css)
        self.assertIn("position: sticky;", self.css)
        self.assertIn("env(safe-area-inset-bottom)", self.css)


if __name__ == "__main__":
    unittest.main()
