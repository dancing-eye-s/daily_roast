#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "downloads" / "copypedia_excels"
RAW_DIR = OUTPUT_DIR / "source_files"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
WORKBOOK_PATH = OUTPUT_DIR / "copypedia_excels_merged.xlsx"

CATEGORY_PAGES = [
    "https://copypedia.tistory.com/category/%EC%B9%B4%ED%94%BC%20%EB%AA%A8%EC%9D%8C?page=1",
    "https://copypedia.tistory.com/category/%EC%B9%B4%ED%94%BC%20%EB%AA%A8%EC%9D%8C?page=2",
    "https://copypedia.tistory.com/category/%EC%B9%B4%ED%94%BC%20%EB%AA%A8%EC%9D%8C?page=3",
    "https://copypedia.tistory.com/category/%EC%B9%B4%ED%94%BC%20%EB%AA%A8%EC%9D%8C?page=4",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


@dataclass
class Article:
    order: int
    title: str
    url: str
    excel_urls: list[str]


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def unique_in_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def fetch_html(client: requests.Session, url: str) -> str:
    response = client.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def extract_article_urls(client: requests.Session) -> list[str]:
    article_urls: list[str] = []
    for page_url in CATEGORY_PAGES:
        soup = BeautifulSoup(fetch_html(client, page_url), "html.parser")
        for anchor in soup.select('a[href*="/entry/"]'):
            href = anchor.get("href")
            if href:
                article_urls.append(urljoin(page_url, href))
    return unique_in_order(article_urls)


def extract_excel_urls(html: str) -> list[str]:
    matches = re.findall(r'https?://[^\\"\'\s<>]+', html)
    excel_urls = [
        candidate
        for candidate in matches
        if any(token in candidate.lower() for token in (".xlsx", ".xls", ".csv"))
    ]
    return unique_in_order(excel_urls)


def collect_articles(client: requests.Session) -> list[Article]:
    articles: list[Article] = []
    for index, article_url in enumerate(extract_article_urls(client), start=1):
        html = fetch_html(client, article_url)
        soup = BeautifulSoup(html, "html.parser")
        meta_title = soup.select_one('meta[property="og:title"]')
        title = meta_title["content"].strip() if meta_title and meta_title.get("content") else article_url
        articles.append(
            Article(
                order=index,
                title=title,
                url=article_url,
                excel_urls=extract_excel_urls(html),
            )
        )
    return articles


def filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    path_name = unquote(Path(parsed.path).name)
    query_name = parse_qs(parsed.query).get("knm", [""])[0]
    if query_name and query_name.lower() not in {"tfile.xlsx", "tfile.xls", "tfile.csv"}:
        return unquote(query_name)
    if path_name:
        return path_name
    if query_name:
        return unquote(query_name)
    return "attachment.xlsx"


def safe_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "file"


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(columns={"Brand Name": "Brand"}).copy()
    for column in ["category", "on-air Date", "Brand", "Copy", "URL"]:
        if column not in renamed.columns:
            renamed[column] = pd.NA
    normalized = renamed[["category", "on-air Date", "Brand", "Copy", "URL"]].copy()
    normalized["on-air Date"] = pd.to_datetime(normalized["on-air Date"], errors="coerce")
    return normalized


def download_and_merge(client: requests.Session, articles: list[Article]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    article_rows: list[dict[str, object]] = []
    file_rows: list[dict[str, object]] = []
    merged_frames: list[pd.DataFrame] = []

    for article in articles:
        article_rows.append(
            {
                "article_order": article.order,
                "article_title": article.title,
                "article_url": article.url,
                "excel_file_count": len(article.excel_urls),
                "has_excel": bool(article.excel_urls),
            }
        )

        for file_index, file_url in enumerate(article.excel_urls, start=1):
            filename = filename_from_url(file_url)
            local_name = f"{article.order:02d}_{file_index:02d}_{safe_stem(filename)}"
            local_path = RAW_DIR / local_name

            response = client.get(file_url, timeout=60)
            response.raise_for_status()
            local_path.write_bytes(response.content)

            workbook = pd.ExcelFile(io.BytesIO(response.content))
            total_rows = 0
            for sheet_name in workbook.sheet_names:
                frame = pd.read_excel(io.BytesIO(response.content), sheet_name=sheet_name, header=1)
                normalized = normalize_frame(frame)
                normalized.insert(0, "article_order", article.order)
                normalized.insert(1, "article_title", article.title)
                normalized.insert(2, "article_url", article.url)
                normalized.insert(3, "source_file_name", filename)
                normalized.insert(4, "source_file_url", file_url)
                normalized.insert(5, "sheet_name", sheet_name)
                normalized.insert(6, "row_number_in_sheet", range(1, len(normalized) + 1))
                merged_frames.append(normalized)
                total_rows += len(normalized)

            file_rows.append(
                {
                    "article_order": article.order,
                    "article_title": article.title,
                    "article_url": article.url,
                    "source_file_name": filename,
                    "source_file_url": file_url,
                    "local_path": str(local_path.relative_to(ROOT)),
                    "sheet_count": len(workbook.sheet_names),
                    "sheet_names": ", ".join(workbook.sheet_names),
                    "row_count": total_rows,
                }
            )

    merged = pd.concat(merged_frames, ignore_index=True) if merged_frames else pd.DataFrame()
    articles_df = pd.DataFrame(article_rows)
    files_df = pd.DataFrame(file_rows)
    return articles_df, files_df, merged


def write_outputs(articles_df: pd.DataFrame, files_df: pd.DataFrame, merged_df: pd.DataFrame) -> None:
    manifest = {
        "article_count": int(len(articles_df)),
        "articles_with_excel": int(articles_df["has_excel"].sum()) if not articles_df.empty else 0,
        "downloaded_file_count": int(len(files_df)),
        "merged_row_count": int(len(merged_df)),
        "output_workbook": str(WORKBOOK_PATH.relative_to(ROOT)),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pd.ExcelWriter(WORKBOOK_PATH, engine="openpyxl") as writer:
        merged_df.to_excel(writer, sheet_name="all_rows", index=False)
        files_df.to_excel(writer, sheet_name="files_index", index=False)
        articles_df.to_excel(writer, sheet_name="articles", index=False)


def main() -> None:
    ensure_dirs()
    client = session()
    articles = collect_articles(client)
    articles_df, files_df, merged_df = download_and_merge(client, articles)
    write_outputs(articles_df, files_df, merged_df)
    print(f"articles: {len(articles_df)}")
    print(f"downloaded_files: {len(files_df)}")
    print(f"merged_rows: {len(merged_df)}")
    print(f"workbook: {WORKBOOK_PATH}")


if __name__ == "__main__":
    main()
