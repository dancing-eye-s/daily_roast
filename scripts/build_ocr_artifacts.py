#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from PIL import Image, ImageOps
from rapidocr_onnxruntime import RapidOCR

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "archive" / "raw"
SEEDS_DIR = ROOT / "archive" / "seeds"
OCR_IMAGE_DIR = RAW_DIR / "ocr_images"
OCR_OUTPUT_DIR = ROOT / "archive" / "ocr"
USER_AGENT = "Mozilla/5.0"

OCR_TARGET_YEARS = {2019, 2017, 2015, 2013}
OCR_ENGINE = RapidOCR()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_image_urls(html: str) -> list[str]:
    urls = []
    for src in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, flags=re.I):
        normalized = src.strip()
        if "thumb.ad.co.kr/article/" not in normalized:
            continue
        if "/i/" not in normalized:
            continue
        if normalized.startswith("//"):
            normalized = "https:" + normalized
        elif normalized.startswith("/"):
            normalized = urljoin("https://ad.co.kr", normalized)
        normalized = normalized.replace("http://", "https://")
        urls.append(normalized)
    deduped = []
    seen = set()
    for url in urls:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
    return deduped


def fetch_image(url: str, path: Path, force: bool = False) -> None:
    if path.exists() and not force:
        return
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)


def preprocess_image(image_path: Path) -> Path:
    processed_path = image_path.with_name(f"{image_path.stem}.processed.png")
    with Image.open(image_path) as img:
        img = img.convert("L")
        img = ImageOps.autocontrast(img)
        img = img.resize((img.width * 2, img.height * 2))
        img.save(processed_path)
    return processed_path


def run_ocr(image_paths: list[Path]) -> list[dict]:
    results: list[dict] = []
    for image_path in image_paths:
        processed_path = preprocess_image(image_path)
        ocr_result, elapse = OCR_ENGINE(str(processed_path))
        lines = []
        if ocr_result:
            for item in ocr_result:
                text = str(item[1]).strip()
                confidence = float(item[2]) if len(item) > 2 else None
                if text:
                    lines.append({"text": text, "confidence": confidence})
        results.append(
            {
                "path": str(image_path),
                "processedPath": str(processed_path),
                "text": "\n".join(line["text"] for line in lines),
                "lines": lines,
                "elapsed": elapse,
            }
        )
    return results


def resolve_cached_html(source_id: str) -> Path:
    candidates = sorted(RAW_DIR.glob(f"{source_id}.*"))
    for candidate in candidates:
        if candidate.suffix in {".do", ".prt", ".mjsp", ".html"}:
            return candidate
    raise FileNotFoundError(f"Could not locate cached HTML for source id {source_id}")


def build_ocr(force_images: bool = False) -> dict:
    source_index = load_json(SEEDS_DIR / "source_index.json")["sources"]
    targets = [
        source
        for source in source_index
        if source.get("year") in OCR_TARGET_YEARS and source.get("role") == "overview"
    ]

    summary = {"generatedAt": utc_now(), "targets": []}
    for source in targets:
        source_id = source["id"]
        html_path = resolve_cached_html(source_id)
        html = html_path.read_text(encoding="utf-8", errors="ignore")
        image_urls = extract_image_urls(html)
        image_paths: list[Path] = []
        for idx, url in enumerate(image_urls, start=1):
            ext = Path(url.split("?")[0]).suffix or ".jpg"
            local_path = OCR_IMAGE_DIR / source_id / f"{idx:03d}{ext}"
            fetch_image(url, local_path, force=force_images)
            image_paths.append(local_path)

        ocr_results = run_ocr(image_paths)
        output_payload = {
            "source": source,
            "htmlPath": str(html_path.relative_to(ROOT)),
            "imageCount": len(image_paths),
            "results": ocr_results,
        }
        output_path = OCR_OUTPUT_DIR / f"{source_id}.json"
        dump_json(output_path, output_payload)
        text_path = OCR_OUTPUT_DIR / f"{source_id}.txt"
        text_path.write_text(
            "\n\n".join(
                f"## {Path(item['path']).name}\n{item.get('text', '')}".strip()
                for item in ocr_results
            )
            + "\n",
            encoding="utf-8",
        )
        summary["targets"].append(
            {
                "id": source_id,
                "year": source["year"],
                "imageCount": len(image_paths),
                "jsonOutput": str(output_path.relative_to(ROOT)),
                "textOutput": str(text_path.relative_to(ROOT)),
            }
        )

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OCR artifacts for image-based award tables.")
    parser.add_argument("--force-images", action="store_true", help="re-download image files")
    args = parser.parse_args()

    summary = build_ocr(force_images=args.force_images)
    dump_json(OCR_OUTPUT_DIR / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
