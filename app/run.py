import sys
import uvicorn
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.matching import build_scored_pairs, load_calendar_records, load_crm_records, evaluate_pairs


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
        return 0

    crm_records = load_crm_records()
    calendar_records = load_calendar_records()
    pairs = build_scored_pairs(crm_records, calendar_records)
    threshold = 0.6
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        threshold = float(sys.argv[1])
    evaluation = evaluate_pairs(pairs, threshold=threshold)
    print("Evaluation results")
    print(f"  threshold   : {evaluation['threshold']}")
    print(f"  precision   : {evaluation['precision']}")
    print(f"  recall      : {evaluation['recall']}")
    print(f"  f1          : {evaluation['f1']}")
    print(f"  accuracy    : {evaluation['accuracy']}")
    print(f"  tp / fp / tn / fn : {evaluation['true_positives']} / {evaluation['false_positives']} / {evaluation['true_negatives']} / {evaluation['false_negatives']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
