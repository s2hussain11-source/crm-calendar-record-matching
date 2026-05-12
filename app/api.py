from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.matching import (
    build_scored_pairs,
    load_calendar_records,
    load_crm_records,
    load_evaluation_labels,
    evaluate_pairs,
    get_prediction_for_pair,
)

app = FastAPI(title="Record Matching Service")
crm_records = load_crm_records()
calendar_records = load_calendar_records()
scored_pairs = build_scored_pairs(crm_records, calendar_records)
labels = load_evaluation_labels()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "crm_records": len(crm_records), "calendar_records": len(calendar_records)}


@app.get("/matches")
def matches(threshold: float = Query(0.6, ge=0.0, le=1.0), limit: Optional[int] = Query(None, ge=1)) -> dict:
    filtered = [pair for pair in scored_pairs if pair["score"] >= threshold]
    if limit is not None:
        filtered = filtered[:limit]
    return {"threshold": threshold, "count": len(filtered), "matches": filtered}


@app.get("/pair")
def pair(crm_id: str, calendar_id: str) -> dict:
    match = get_prediction_for_pair(crm_id, calendar_id, scored_pairs)
    if not match:
        raise HTTPException(status_code=404, detail="Pair not found")
    return match


@app.get("/evaluate")
def evaluate(threshold: float = Query(0.6, ge=0.0, le=1.0)) -> dict:
    return evaluate_pairs(scored_pairs, threshold=threshold)
