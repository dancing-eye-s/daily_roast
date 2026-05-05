#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENTRIES_PATH = ROOT / "archive" / "seeds" / "entries.seed.json"
OCR_CANDIDATES_PATH = ROOT / "archive" / "ocr" / "parsed_candidates.json"
PROMOTION_REPORT_PATH = ROOT / "archive" / "ocr" / "promotion_report.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def seed_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item["year"],
        item["awardLevel"],
        item["brand"],
        item["campaign"],
    )


def convert_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": candidate["id"],
        "year": candidate["year"],
        "awardLevel": candidate["awardLevel"],
        "awardCategory": candidate["awardCategory"],
        "brand": candidate["brand"],
        "campaign": candidate["campaign"],
        "copy": candidate["copy"],
        "detail": candidate["detail"],
        "sourceType": candidate["sourceType"],
        "sourceKind": "article",
        "sourceUrl": candidate["sourceUrl"],
        "copyStatus": candidate["copyStatus"],
        "notes": {
            "promotedFrom": "ocr-candidate",
            "sourceId": candidate["sourceId"],
            "confidence": candidate["confidence"],
            "matchedPatterns": candidate["matchedPatterns"],
            "ocrJson": candidate["ocrJson"],
            "ocrText": candidate["ocrText"],
        },
    }


def promote(min_confidence: float, dry_run: bool = False) -> dict[str, Any]:
    entries = load_json(ENTRIES_PATH)
    candidates_payload = load_json(OCR_CANDIDATES_PATH)
    candidates = candidates_payload["candidates"]

    existing_keys = {seed_key(entry) for entry in entries}
    selected: list[dict[str, Any]] = []
    skipped_low_conf: list[dict[str, Any]] = []
    skipped_duplicate: list[dict[str, Any]] = []

    for candidate in candidates:
        if float(candidate["confidence"]) < min_confidence:
            skipped_low_conf.append(candidate)
            continue
        key = seed_key(candidate)
        if key in existing_keys:
            skipped_duplicate.append(candidate)
            continue
        selected.append(candidate)
        existing_keys.add(key)

    promoted_entries = [convert_candidate(candidate) for candidate in selected]

    if not dry_run and promoted_entries:
        updated_entries = entries + promoted_entries
        updated_entries.sort(
            key=lambda item: (-item["year"], item["brand"], item["campaign"], item["awardLevel"])
        )
        dump_json(ENTRIES_PATH, updated_entries)

    report = {
        "generatedAt": utc_now(),
        "minConfidence": min_confidence,
        "dryRun": dry_run,
        "candidateCount": len(candidates),
        "promotedCount": len(promoted_entries),
        "skippedLowConfidenceCount": len(skipped_low_conf),
        "skippedDuplicateCount": len(skipped_duplicate),
        "promoted": [
            {
                "id": candidate["id"],
                "year": candidate["year"],
                "awardLevel": candidate["awardLevel"],
                "brand": candidate["brand"],
                "campaign": candidate["campaign"],
                "confidence": candidate["confidence"],
            }
            for candidate in selected
        ],
    }
    dump_json(PROMOTION_REPORT_PATH, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote high-confidence OCR candidates into entries.seed.json")
    parser.add_argument("--min-confidence", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = promote(min_confidence=args.min_confidence, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
