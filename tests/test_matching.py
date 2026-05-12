import unittest
from datetime import date, time, datetime
from app.matching import (
    normalize_text,
    parse_crm_date,
    parse_crm_time,
    parse_calendar_datetime,
    is_virtual_location,
    sequence_similarity,
    company_similarity,
    parse_crm_record,
    parse_calendar_record,
    score_datetime,
    score_client,
    score_location,
    score_owner_attendee,
    match_score,
    evaluate_pairs,
    load_evaluation_labels,
)


class TestNormalization(unittest.TestCase):
    def test_normalize_text_basic(self):
        self.assertEqual(normalize_text("Hello World!"), "hello world")
        self.assertEqual(normalize_text("  Test  "), "test")
        self.assertIsNone(normalize_text(None))
        self.assertIsNone(normalize_text(""))

    def test_normalize_text_special_chars(self):
        self.assertEqual(normalize_text("Don't worry"), "don t worry")
        self.assertEqual(normalize_text("Test@Example.com"), "test@example.com")


class TestDateTimeParsing(unittest.TestCase):
    def test_parse_crm_date_standard(self):
        self.assertEqual(parse_crm_date("2025-03-10"), date(2025, 3, 10))

    def test_parse_crm_date_malformed(self):
        self.assertEqual(parse_crm_date("03-15/2025"), date(2025, 3, 15))
        self.assertIsNone(parse_crm_date("invalid"))

    def test_parse_crm_time(self):
        self.assertEqual(parse_crm_time("14:00"), time(14, 0))
        self.assertEqual(parse_crm_time("2:30 PM"), time(14, 30))
        self.assertIsNone(parse_crm_time("invalid"))

    def test_parse_calendar_datetime(self):
        self.assertEqual(parse_calendar_datetime("2025-03-10T14:00:00"), datetime(2025, 3, 10, 14, 0))
        dt = parse_calendar_datetime("2025-03-10T14:00:00Z")
        self.assertEqual(dt.replace(tzinfo=None), datetime(2025, 3, 10, 14, 0))


class TestVirtualDetection(unittest.TestCase):
    def test_is_virtual_location(self):
        self.assertTrue(is_virtual_location("Zoom meeting"))
        self.assertFalse(is_virtual_location("Conference Room B"))
        self.assertFalse(is_virtual_location(None))


class TestSimilarity(unittest.TestCase):
    def test_sequence_similarity(self):
        self.assertEqual(sequence_similarity("hello", "hello"), 1.0)
        self.assertLess(sequence_similarity("hello", "world"), 1.0)

    def test_company_similarity(self):
        self.assertEqual(company_similarity("ABC Inc", "ABC Inc"), 1.0)
        self.assertEqual(company_similarity("ABC Inc", "ABC LLC"), sequence_similarity("abc", "abc"))


class TestRecordParsing(unittest.TestCase):
    def test_parse_crm_record(self):
        record = {
            "crm_id": "CRM-1001",
            "subject": "Test Meeting",
            "client_name": "John Doe",
            "client_company": "Test Corp",
            "relationship_owner": "Jane Smith",
            "meeting_date": "2025-03-10",
            "meeting_time": "14:00",
            "meeting_type": "In-Person",
            "location": "Room A",
            "notes": "Test notes",
            "status": "Confirmed",
            "created_at": "2025-03-01T10:00:00Z"
        }
        crm = parse_crm_record(record)
        self.assertEqual(crm.crm_id, "CRM-1001")
        self.assertEqual(crm.meeting_date, date(2025, 3, 10))
        self.assertEqual(crm.meeting_time, time(14, 0))
        self.assertEqual(crm.normalized["subject"], "test meeting")

    def test_parse_calendar_record(self):
        record = {
            "event_id": "CAL-A1",
            "title": "Test Event",
            "organizer": "organizer@example.com",
            "attendees": ["attendee@example.com"],
            "start_time": "2025-03-10T14:00:00",
            "end_time": "2025-03-10T15:00:00",
            "location": "Virtual",
            "description": "Test description",
            "is_recurring": False,
            "status": "confirmed",
            "created_at": "2025-03-01T10:00:00Z"
        }
        cal = parse_calendar_record(record)
        self.assertEqual(cal.calendar_id, "CAL-A1")
        self.assertEqual(cal.start_time, datetime(2025, 3, 10, 14, 0))
        self.assertEqual(cal.normalized["title"], "test event")


class TestScoring(unittest.TestCase):
    def test_score_datetime_exact_match(self):
        crm = parse_crm_record({"meeting_date": "2025-03-10", "meeting_time": "14:00"})
        cal = parse_calendar_record({"start_time": "2025-03-10T14:00:00"})
        date_score, time_score = score_datetime(crm, cal)
        self.assertEqual(date_score, 1.0)
        self.assertEqual(time_score, 1.0)

    def test_score_datetime_no_match(self):
        crm = parse_crm_record({"meeting_date": "2025-03-10", "meeting_time": "14:00"})
        cal = parse_calendar_record({"start_time": "2025-03-11T15:00:00"})
        date_score, time_score = score_datetime(crm, cal)
        self.assertEqual(date_score, 0.0)
        self.assertLess(time_score, 1.0)

    def test_score_client(self):
        crm = parse_crm_record({"subject": "Portfolio Review", "client_name": "John Doe", "client_company": "Test Corp"})
        cal = parse_calendar_record({"title": "Portfolio Review - Test Corp"})
        score = score_client(crm, cal)
        self.assertGreater(score, 0.5)  # Should be high due to title and company match

    def test_score_location_virtual(self):
        crm = parse_crm_record({"location": "Zoom"})
        cal = parse_calendar_record({"location": "Microsoft Teams"})
        score = score_location(crm, cal)
        self.assertEqual(score, 1.0)  # Both virtual

    def test_score_location_physical(self):
        crm = parse_crm_record({"location": "Room A"})
        cal = parse_calendar_record({"location": "Room B"})
        score = score_location(crm, cal)
        self.assertLess(score, 1.0)  # Different locations

    def test_score_owner_attendee(self):
        crm = parse_crm_record({"relationship_owner": "Jane Smith"})
        cal = parse_calendar_record({"organizer": "jane smith", "attendees": ["jane.smith@example.com"]})
        score = score_owner_attendee(crm, cal)
        self.assertEqual(score, 1.0)  # Exact match with organizer
        self.assertEqual(score, 1.0)  # Exact match

    def test_match_score(self):
        crm = parse_crm_record({
            "crm_id": "CRM-1001",
            "subject": "Test Meeting",
            "meeting_date": "2025-03-10",
            "meeting_time": "14:00",
            "location": "Room A",
            "relationship_owner": "Jane Smith"
        })
        cal = parse_calendar_record({
            "event_id": "CAL-A1",
            "title": "Test Meeting",
            "start_time": "2025-03-10T14:00:00",
            "location": "Room A",
            "organizer": "jane.smith@example.com"
        })
        result = match_score(crm, cal)
        self.assertGreater(result["score"], 0.8)  # High score for good match
        self.assertIn("features", result)


class TestEvaluation(unittest.TestCase):
    def test_evaluate_pairs(self):
        # Mock pairs and labels
        pairs = [
            {"crm_id": "CRM-1001", "calendar_id": "CAL-A1", "score": 0.9, "features": {}},
            {"crm_id": "CRM-1002", "calendar_id": "CAL-A2", "score": 0.3, "features": {}}
        ]
        labels = [
            {"crm_id": "CRM-1001", "calendar_id": "CAL-A1", "match": True},
            {"crm_id": "CRM-1002", "calendar_id": "CAL-A2", "match": False}
        ]
        import app.matching
        original_load = app.matching.load_evaluation_labels
        app.matching.load_evaluation_labels = lambda: labels
        try:
            result = evaluate_pairs(pairs, threshold=0.5)
            self.assertEqual(result["precision"], 1.0)  # 1 TP, 0 FP
            self.assertEqual(result["recall"], 1.0)     # 1 TP, 0 FN
            self.assertEqual(result["f1"], 1.0)
        finally:
            app.matching.load_evaluation_labels = original_load


if __name__ == '__main__':
    unittest.main()