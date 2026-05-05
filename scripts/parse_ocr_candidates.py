#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OCR_DIR = ROOT / "archive" / "ocr"
OUTPUT_JSON = OCR_DIR / "parsed_candidates.json"
OUTPUT_MD = OCR_DIR / "parsed_candidates.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def slug_fragment(value: str) -> str:
    value = normalize_text(value).lower()
    value = re.sub(r"[^0-9a-zA-Z가-힣]+", "-", value)
    return value.strip("-") or "entry"


@dataclass
class PatternRule:
    year: int
    source_id: str
    award_level: str
    award_category: str
    brand: str
    campaign: str
    patterns: list[str]
    detail: str = "OCR 패턴 정제 후보"


RULES: list[PatternRule] = [
    PatternRule(2019, "opad-2019-overview", "대상", "TV광고", "LG TROMM 트윈워시", "한국인의 세탁", [r"LG5G", r"\bTV\b"]),
    PatternRule(2019, "opad-2019-overview", "대상", "통합미디어", "미원", "미필적 선의", [r"Re-AD", r"reADY", r"KoreaAdvertisingAwards"]),
    PatternRule(2017, "adco-2017-overview", "대상", "라디오", "한화그룹", "당신의 불꽃은 무엇입니까", [r"2017", r"KOREAADVERTISINGAWARDS"]),
    PatternRule(2015, "opad-2015-overview", "대상", "옥외 / 온라인 / 통합미디어", "현대자동차", "A Message to Space", [r"A\s*Message\s*to\s*Space", r"AMessagetoSpace"]),
    PatternRule(2015, "opad-2015-overview", "금상", "영상", "삼성", "SMART SUIT", [r"SMART SUIT"]),
    PatternRule(2015, "opad-2015-overview", "은상", "영상", "LG OLED TV, G3, LG G Watch R", "Who ruined Jenny's wedding?", [r"Jennyswedding", r"WHORUINEDJENNY"]),
    PatternRule(2015, "opad-2015-overview", "은상", "프로모션", "코웨이", "Water Program", [r"WaterProgram", r"Coway"]),
    PatternRule(2015, "opad-2015-overview", "동상", "영상", "삼성 Curved UHD TV", "Detail", [r"Samsung Curved", r"Detail"]),
    PatternRule(2015, "opad-2015-overview", "금상", "디지털", "리복", "Go Dynamic", [r"Go Dynanic", r"Go Dynamic"]),
    PatternRule(2015, "opad-2015-overview", "은상", "브랜디드콘텐츠", "현대자동차", "CAR TO CAR The surprise at drive in theater", [r"CAR TO CAR", r"drive in theot"]),
    PatternRule(2013, "opad-2013-overview", "대상", "인쇄", "LG전자 스타일러", "스타일러 없었으면 짜증 좀 났을 거다", [r"LGOEDTV", r"EifesGoed", r"스타일러"]),
    PatternRule(2013, "opad-2013-overview", "대상", "디자인", "야생생물관리협회", "Tape for Wildlife", [r"TV早足", r"DonationToy", r"Sticky Morster"]),
    PatternRule(2013, "opad-2013-overview", "금상", "영상", "대한항공", "Around the World in 80 Seconds", [r"Around the Wortd in 80 Seconds", r"by Korean Ar"]),
    PatternRule(2013, "opad-2013-overview", "은상", "프로모션", "맥도날드", "Wake up with McMorning", [r"Wake up wth McMoning", r"McMoning"]),
    PatternRule(2013, "opad-2013-overview", "동상", "디지털", "SK텔레콤", "LTE WARP", [r"LTE WARP"]),
    PatternRule(2013, "opad-2013-overview", "특별상", "브랜디드 필름", "삼성 스마트TV", "Let's Look Up", [r"Lat's Look Up", r"Let.?s Look Up"]),
    PatternRule(2013, "opad-2013-overview", "특별상", "CSR", "Donation Toy", "Donation Toy", [r"Doneton Toy", r"Donation Toy"]),
]


def load_ocr_file(source_id: str) -> dict[str, Any]:
    path = OCR_DIR / f"{source_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def source_corpus(data: dict[str, Any]) -> str:
    chunks = []
    for item in data.get("results", []):
        chunks.append(item.get("text", ""))
    return "\n".join(chunks)


def find_matches(corpus: str, patterns: list[str]) -> list[str]:
    matched = []
    for pattern in patterns:
        if re.search(pattern, corpus, flags=re.I):
            matched.append(pattern)
    return matched


def build_candidates() -> dict[str, Any]:
    grouped_sources: dict[str, dict[str, Any]] = {}
    for rule in RULES:
        if rule.source_id not in grouped_sources:
            grouped_sources[rule.source_id] = load_ocr_file(rule.source_id)

    candidates: list[dict[str, Any]] = []
    for index, rule in enumerate(RULES, start=1):
        ocr_data = grouped_sources[rule.source_id]
        corpus = source_corpus(ocr_data)
        matched = find_matches(corpus, rule.patterns)
        confidence = round(len(matched) / max(len(rule.patterns), 1), 2)
        candidates.append(
            {
                "id": f"ocr-{rule.year}-{slug_fragment(rule.brand)}-{slug_fragment(rule.campaign)}-{index}",
                "year": rule.year,
                "sourceId": rule.source_id,
                "awardLevel": rule.award_level,
                "awardCategory": rule.award_category,
                "brand": rule.brand,
                "campaign": rule.campaign,
                "copy": rule.campaign,
                "detail": rule.detail,
                "sourceType": "OCR 이미지형 수상표 정제 후보",
                "copyStatus": "inferred",
                "matchedPatterns": matched,
                "patternCount": len(rule.patterns),
                "confidence": confidence,
                "sourceUrl": grouped_sources[rule.source_id]["source"]["url"],
                "ocrJson": str((OCR_DIR / f"{rule.source_id}.json").relative_to(ROOT)),
                "ocrText": str((OCR_DIR / f"{rule.source_id}.txt").relative_to(ROOT)),
            }
        )

    payload = {
        "generatedAt": utc_now(),
        "candidateCount": len(candidates),
        "candidates": candidates,
    }
    return payload


def write_outputs(payload: dict[str, Any]) -> None:
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# OCR Parsed Candidates",
        "",
        f"- generatedAt: {payload['generatedAt']}",
        f"- candidateCount: {payload['candidateCount']}",
        "",
    ]
    for item in payload["candidates"]:
        lines.append(
            f"- {item['year']} | {item['awardLevel']} | {item['brand']} | {item['campaign']} | confidence={item['confidence']}"
        )
        lines.append(f"  source: {item['sourceId']}")
        lines.append(f"  matchedPatterns: {', '.join(item['matchedPatterns']) or 'none'}")
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse OCR artifacts into review-ready award candidates.")
    parser.parse_args()
    payload = build_candidates()
    write_outputs(payload)
    print(json.dumps({"generatedAt": payload["generatedAt"], "candidateCount": payload["candidateCount"], "output": str(OUTPUT_JSON.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
