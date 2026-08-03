import importlib.util
import unittest
from datetime import datetime
from pathlib import Path


def load(name):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


history = load("emotion_history_83")
writer = load("emotion_write_83")


class HistoryTests(unittest.TestCase):
    def test_summary_and_daily_trend(self):
        rows = [
            {"timestamp": datetime(2026, 8, 1, 8), "dominant": "happy", "conflict": 0.2, "high_conflict": 0},
            {"timestamp": datetime(2026, 8, 1, 9), "dominant": "sad", "conflict": 0.8, "high_conflict": 1},
            {"timestamp": datetime(2026, 8, 2, 9), "dominant": "happy", "conflict": 0.1, "high_conflict": 0},
        ]
        self.assertEqual(history._summary(rows), {
            "total": 3, "dominantTop": "happy", "avgK": 0.3667, "highConflictCount": 1,
        })
        self.assertEqual(history._trend(rows, "day")["happy"], [50.0, 100.0])
        self.assertEqual(history._trend(rows, "hour")["labels"], [
            "2026-08-01 08:00", "2026-08-01 09:00", "2026-08-02 09:00",
        ])

    def test_invalid_date_range(self):
        with self.assertRaisesRegex(ValueError, "start"):
            history._filters({"start": "2026-08-03", "end": "2026-08-01"})


class WriteValidationTests(unittest.TestCase):
    def test_valid_payload(self):
        result = writer._validate({
            "device_id": "esp32-01", "dominant": "happy", "score": 0.6,
            "belief": [0.6, 0.1, 0.2, 0.1], "conflict": 0.2,
        })
        self.assertEqual(result["device_id"], "esp32-01")

    def test_empty_payload_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "device_id"):
            writer._validate({})


if __name__ == "__main__":
    unittest.main()
