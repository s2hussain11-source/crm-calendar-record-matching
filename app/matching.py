import json
import re
from dataclasses import dataclass
from datetime import datetime, date, time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).parent.parent / "data"

VIRTUAL_KEYWORDS = ["zoom", "teams", "microsoft teams", "virtual", "call", "webex", "google meet"]

@dataclass
class CRMRecord:
    crm_id: str
    subject: str
    client_name: Optional[str]
    client_company: Optional[str]
    relationship_owner: Optional[str]
    meeting_date: Optional[date]
    meeting_time: Optional[time]
    meeting_type: Optional[str]
    location: Optional[str]
    notes: Optional[str]
    status: Optional[str]
    created_at: Optional[datetime]
    normalized: Dict[str, Any] = None


@dataclass
class CalendarRecord:
    calendar_id: str
    title: str
    organizer: Optional[str]
    attendees: List[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    location: Optional[str]
    description: Optional[str]
    is_recurring: bool = False
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    normalized: Dict[str, Any] = None


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip().lower()
    text = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", text)
    text = re.sub(r"[^a-z0-9@\s\-\\/\.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_crm_date(value: Optional[str]) -> Optional[date]:
    if value is None:
        return None
    value = value.strip()
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        pass
    match = re.match(r"^(\d{1,2})-(\d{1,2})/(\d{4})$", value)
    if match:
        month, day, year = match.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            return None
    for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(value, fmt).date()
        except Exception:
            continue
    return None


def parse_crm_time(value: Optional[str]) -> Optional[time]:
    if value is None:
        return None
    value = value.strip()
    for fmt in ["%H:%M", "%H:%M:%S", "%I:%M %p", "%I %p"]:
        try:
            return datetime.strptime(value, fmt).time()
        except Exception:
            continue
    return None


def parse_calendar_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        # clean common timezone indicators
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None


def is_virtual_location(text: Optional[str]) -> bool:
    if not text:
        return False
    text = normalize_text(text)
    return any(keyword in text for keyword in VIRTUAL_KEYWORDS)


def tokenize_text(value: Optional[str]) -> List[str]:
    if not value:
        return []
    text = normalize_text(value)
    if not text:
        return []
    return [token for token in text.split() if len(token) > 1]


def sequence_similarity(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def company_similarity(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    a_norm = normalize_text(a).replace("inc", "").replace("ltd", "").replace("llc", "")
    b_norm = normalize_text(b).replace("inc", "").replace("ltd", "").replace("llc", "")
    return sequence_similarity(a_norm, b_norm)


def name_similarity(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    return sequence_similarity(normalize_text(a), normalize_text(b))


def parse_crm_record(record: Dict[str, Any]) -> CRMRecord:
    meeting_date = parse_crm_date(record.get("meeting_date"))
    meeting_time = parse_crm_time(record.get("meeting_time"))
    created_at = parse_calendar_datetime(record.get("created_at"))
    normalized_subject = normalize_text(record.get("subject"))
    normalized_location = normalize_text(record.get("location"))
    return CRMRecord(
        crm_id=record.get("crm_id"),
        subject=record.get("subject", ""),
        client_name=record.get("client_name"),
        client_company=record.get("client_company"),
        relationship_owner=record.get("relationship_owner"),
        meeting_date=meeting_date,
        meeting_time=meeting_time,
        meeting_type=record.get("meeting_type"),
        location=record.get("location"),
        notes=record.get("notes"),
        status=record.get("status"),
        created_at=created_at,
        normalized={
            "subject": normalized_subject,
            "location": normalized_location,
            "client_name": normalize_text(record.get("client_name")),
            "client_company": normalize_text(record.get("client_company")),
            "relationship_owner": normalize_text(record.get("relationship_owner")),
            "is_virtual": is_virtual_location(record.get("location") or record.get("meeting_type")),
        },
    )


def parse_calendar_record(record: Dict[str, Any]) -> CalendarRecord:
    start_time = parse_calendar_datetime(record.get("start_time"))
    end_time = parse_calendar_datetime(record.get("end_time"))
    created_at = parse_calendar_datetime(record.get("created_at"))
    normalized_title = normalize_text(record.get("title"))
    normalized_location = normalize_text(record.get("location"))
    organizer = normalize_text(record.get("organizer"))
    attendees = [normalize_text(email) for email in record.get("attendees") or [] if normalize_text(email)]
    return CalendarRecord(
        calendar_id=record.get("event_id"),
        title=record.get("title", ""),
        organizer=organizer,
        attendees=attendees,
        start_time=start_time,
        end_time=end_time,
        location=record.get("location"),
        description=record.get("description"),
        is_recurring=bool(record.get("is_recurring")),
        status=record.get("status"),
        created_at=created_at,
        normalized={
            "title": normalized_title,
            "location": normalized_location,
            "description": normalize_text(record.get("description")),
            "organizer": organizer,
            "is_virtual": is_virtual_location(record.get("location") or record.get("title") or record.get("description")),
        },
    )


def load_crm_records() -> List[CRMRecord]:
    raw = load_json(DATA_DIR / "crm_events.json")
    return [parse_crm_record(record) for record in raw]


def load_calendar_records() -> List[CalendarRecord]:
    raw = load_json(DATA_DIR / "calendar_events.json")
    return [parse_calendar_record(record) for record in raw]


def time_diff_minutes(a: Optional[time], b: Optional[time]) -> Optional[int]:
    if a is None or b is None:
        return None
    delta = datetime.combine(date.min, a) - datetime.combine(date.min, b)
    return abs(int(delta.total_seconds() / 60))


def score_datetime(crm: CRMRecord, cal: CalendarRecord) -> Tuple[float, float]:
    date_score = 0.0
    time_score = 0.0
    if crm.meeting_date and cal.start_time:
        date_score = 1.0 if crm.meeting_date == cal.start_time.date() else 0.0
    if crm.meeting_time and cal.start_time:
        diff = time_diff_minutes(crm.meeting_time, cal.start_time.time())
        if diff is not None:
            if diff <= 15:
                time_score = 1.0
            elif diff <= 60:
                time_score = 0.6
            elif diff <= 120:
                time_score = 0.3
    return date_score, time_score


def score_client(crm: CRMRecord, cal: CalendarRecord) -> float:
    subject_score = sequence_similarity(crm.normalized["subject"], cal.normalized["title"])
    company_score = company_similarity(crm.normalized["client_company"], None)
    client_score = 0.0
    if crm.client_name and cal.title:
        client_score = sequence_similarity(normalize_text(crm.client_name), normalize_text(cal.title))
    if crm.client_company and cal.title:
        company_title_score = sequence_similarity(normalize_text(crm.client_company), normalize_text(cal.title))
        client_score = max(client_score, company_title_score)
    if crm.client_name and crm.client_company:
        return max(subject_score * 0.4 + client_score * 0.6, client_score)
    return max(subject_score, client_score)


def score_location(crm: CRMRecord, cal: CalendarRecord) -> float:
    crm_virtual = crm.normalized["is_virtual"]
    cal_virtual = cal.normalized["is_virtual"]
    if crm_virtual and cal_virtual:
        return 1.0
    if crm_virtual != cal_virtual:
        return 0.0
    if crm.normalized["location"] and cal.normalized["location"]:
        return sequence_similarity(crm.normalized["location"], cal.normalized["location"])
    return 0.0


def score_owner_attendee(crm: CRMRecord, cal: CalendarRecord) -> float:
    if not crm.relationship_owner:
        return 0.0
    owner = normalize_text(crm.relationship_owner)
    if not owner:
        return 0.0
    if owner in (cal.organizer or ""):
        return 1.0
    if any(owner.split()[0] in attendee for attendee in cal.attendees if attendee):
        return 0.8
    return 0.0


def match_score(crm: CRMRecord, cal: CalendarRecord) -> Dict[str, Any]:
    date_score, time_score = score_datetime(crm, cal)
    title_score = sequence_similarity(crm.normalized["subject"], cal.normalized["title"])
    client_score = score_client(crm, cal)
    location_score = score_location(crm, cal)
    owner_score = score_owner_attendee(crm, cal)
    feature_weights = {
        "date": 0.25,
        "time": 0.20,
        "title": 0.15,
        "client": 0.20,
        "location": 0.10,
        "owner": 0.10,
    }
    score = (
        date_score * feature_weights["date"]
        + time_score * feature_weights["time"]
        + title_score * feature_weights["title"]
        + client_score * feature_weights["client"]
        + location_score * feature_weights["location"]
        + owner_score * feature_weights["owner"]
    )
    return {
        "crm_id": crm.crm_id,
        "calendar_id": cal.calendar_id,
        "score": round(score, 4),
        "features": {
            "date": round(date_score, 3),
            "time": round(time_score, 3),
            "title": round(title_score, 3),
            "client": round(client_score, 3),
            "location": round(location_score, 3),
            "owner": round(owner_score, 3),
        },
    }


def build_scored_pairs(crm_records: List[CRMRecord], calendar_records: List[CalendarRecord]) -> List[Dict[str, Any]]:
    pairs = []
    for crm in crm_records:
        for cal in calendar_records:
            pairs.append(match_score(crm, cal))
    return sorted(pairs, key=lambda item: item["score"], reverse=True)


def load_evaluation_labels() -> List[Dict[str, Any]]:
    raw = load_json(DATA_DIR / "evaluation_labels.json")
    return raw.get("cross_source_pairs", [])


def evaluate_pairs(pairs: List[Dict[str, Any]], threshold: float = 0.6) -> Dict[str, Any]:
    labels = load_evaluation_labels()
    label_map = {f"{item['crm_id']}|{item['calendar_id']}": item["match"] for item in labels}
    tp = fp = tn = fn = 0
    details = []
    pair_index = {f"{item['crm_id']}|{item['calendar_id']}": item for item in pairs}
    for key, actual in label_map.items():
        predicted = pair_index.get(key)
        if predicted is None:
            continue
        match_pred = predicted["score"] >= threshold
        if match_pred and actual:
            tp += 1
        elif match_pred and not actual:
            fp += 1
        elif not match_pred and actual:
            fn += 1
        elif not match_pred and not actual:
            tn += 1
        details.append({
            "crm_id": predicted["crm_id"],
            "calendar_id": predicted["calendar_id"],
            "score": predicted["score"],
            "predicted_match": match_pred,
            "actual_match": actual,
            "features": predicted["features"],
        })
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if tp + tn + fp + fn else 0.0
    return {
        "threshold": threshold,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "details": details,
    }


def get_prediction_for_pair(crm_id: str, calendar_id: str, pairs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    key = f"{crm_id}|{calendar_id}"
    for pair in pairs:
        if pair["crm_id"] == crm_id and pair["calendar_id"] == calendar_id:
            return pair
    return None
