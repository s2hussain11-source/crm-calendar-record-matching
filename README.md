# Record Matching System

## Quick Start

```bash
pip install -r requirements.txt
python app/run.py serve
```

API docs:

```txt
http://localhost:8000/docs
```

## Problem Statement

The objective is to identify whether CRM meeting records and calendar events refer to the same real-world meeting despite inconsistencies in formatting, timestamps, naming, and missing fields.

The provided dataset intentionally contains noisy data such as:
- partial ground truth labels
- missing client/contact/location values
- inconsistent timestamp formatting and UTC "Z" indicators
- duplicate or overlapping events within the same source
- virtual vs in-person meeting descriptions

This system predicts likely matches between CRM and calendar records, assigns a confidence score, and evaluates performance against the provided labeled pairs.

## Project Structure

```
record-matching-system/
│
├── app/
│   ├── api.py
│   ├── matching.py
│   └── run.py
│
├── data/
│   ├── crm_events.json
│   ├── calendar_events.json
│   └── evaluation_labels.json
│
├── tests/
│   ├── test_api.py
│   └── test_matching.py
│
├── requirements.txt
└── README.md
```

## How to run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run unit tests:

```bash
python -m unittest discover tests
```

3. Evaluate the matching system:

```bash
python app/run.py
```

or

```bash
python -m app.run
```

4. Start the API service:

```bash
python app/run.py serve
```

or

```bash
python -m app.run serve
```

If `uvicorn` is installed globally, this also works:

```bash
uvicorn app.api:app --reload
```

## API Endpoints

- `GET /health`
- `GET /matches?threshold=0.6&limit=10`
- `GET /pair?crm_id=CRM-1001&calendar_id=CAL-A1`
- `GET /evaluate?threshold=0.6`

## Approach

A rule-based similarity scoring system was used instead of a trained ML model.
The goal was to maximize explainability while remaining robust to noisy business data.

### Why rule-based scoring?

The dataset is relatively small and the labels are partial. A supervised model would risk overfitting and provide less interpretable predictions. Weighted scoring is transparent, easier to debug, and more appropriate for structured business meeting data.

### Matching signals

The system evaluates candidate CRM/calendar pairs using multiple features:

| Signal | Purpose |
|--------|---------|
| Date similarity | Strongest signal for matching the same meeting day |
| Time similarity | Allows tolerance for scheduling drift between systems |
| Title/subject similarity | Captures wording variations and structured meeting names |
| Client/company similarity | Links the same customer relationship across sources |
| Location similarity | Matches physical venue or virtual meeting indicators |
| Relationship owner similarity | Connects CRM owners to calendar organizers/attendees |

Each signal is combined into a weighted confidence score, allowing the API to expose both the final score and feature-level contributions.

## Data Quality Handling

The implementation explicitly handles real-world data issues present in the dataset:

- **Malformed dates**: supports inconsistent CRM date formats like `03-15/2025` in addition to ISO dates.
- **Timezone normalization**: normalizes calendar timestamps using UTC `Z` when present.
- **Missing values**: gracefully handles missing location, time, owner, and attendee fields.
- **Text normalization**: lowercasing, punctuation cleanup, and fuzzy similarity reduce noise from formatting differences.
- **Partial labels**: evaluation only uses the provided labeled pairs and does not assume unlabeled pairs are negatives.

## Evaluation Results

Evaluation is performed on the provided partial ground truth labels using a threshold of `0.6`.

The threshold of `0.6` was selected after experimentation because it provided the best balance between precision and recall on the provided labeled examples while minimizing  false positives.

| Metric | Value |
|--------|-------|
| Precision | 1.00 |
| Recall | 1.00 |
| F1 Score | 1.00 |
| Accuracy | 1.00 |

> Note: these metrics are calculated only on the labeled pairs in `data/evaluation_labels.json`.

## Example API Response

Request:

```http
GET /pair?crm_id=CRM-1001&calendar_id=CAL-A1
```

Example response:

```json
{
  "crm_id": "CRM-1001",
  "calendar_id": "CAL-A1",
  "score": 0.8416,
  "features": {
    "date": 1.0,
    "time": 1.0,
    "title": 0.667,
    "client": 0.622,
    "location": 0.872,
    "owner": 0.8
  }
}
```

This output demonstrates the system's explainability by exposing both the overall confidence and individual matching signal contributions.

## AI Usage

AI-assisted development tools were used to accelerate scaffolding, implementation exploration, and code review during development.

All matching logic, scoring strategies, evaluation methodology, and final implementation decisions were manually reviewed and adjusted to ensure correctness, explainability, and alignment with the problem requirements.

## Future Improvements

Possible next steps include:

- more advanced blocking to reduce candidate pair comparisons for larger datasets
- improved owner/email matching logic for stronger relationship-owner signals
- learned ranking or ML-based weighting if a larger labeled dataset becomes available
- richer error analysis on false positives/negatives beyond the provided labels
