#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = ROOT / "downloads" / "copypedia_excels" / "copypedia_excels_merged.xlsx"

SORT_COLUMNS = [
    "on-air Date",
    "article_order",
    "source_file_name",
    "sheet_name",
    "row_number_in_sheet",
]
DEDUP_COLUMNS = ["on-air Date", "Brand", "Copy"]


def build_monthly_sorted_frame(all_rows: pd.DataFrame) -> pd.DataFrame:
    frame = all_rows.copy()
    frame["on-air Date"] = pd.to_datetime(frame["on-air Date"], errors="coerce")
    frame["year_month"] = frame["on-air Date"].dt.strftime("%Y-%m")
    frame = frame.sort_values(SORT_COLUMNS, kind="stable").reset_index(drop=True)
    ordered_columns = [
        "year_month",
        "on-air Date",
        "category",
        "Brand",
        "Copy",
        "URL",
        "article_title",
        "source_file_name",
        "article_url",
        "source_file_url",
        "article_order",
        "sheet_name",
        "row_number_in_sheet",
    ]
    return frame[ordered_columns]


def build_deduped_frame(monthly_sorted: pd.DataFrame) -> pd.DataFrame:
    deduped = monthly_sorted.drop_duplicates(subset=DEDUP_COLUMNS, keep="first").reset_index(drop=True)
    return deduped


def main() -> None:
    all_rows = pd.read_excel(WORKBOOK_PATH, sheet_name="all_rows")
    files_index = pd.read_excel(WORKBOOK_PATH, sheet_name="files_index")
    articles = pd.read_excel(WORKBOOK_PATH, sheet_name="articles")

    monthly_sorted = build_monthly_sorted_frame(all_rows)
    deduped = build_deduped_frame(monthly_sorted)

    with pd.ExcelWriter(WORKBOOK_PATH, engine="openpyxl") as writer:
        all_rows.to_excel(writer, sheet_name="all_rows", index=False)
        monthly_sorted.to_excel(writer, sheet_name="all_rows_monthly", index=False)
        deduped.to_excel(writer, sheet_name="all_rows_deduped", index=False)
        files_index.to_excel(writer, sheet_name="files_index", index=False)
        articles.to_excel(writer, sheet_name="articles", index=False)

    print(f"all_rows: {len(all_rows)}")
    print(f"all_rows_monthly: {len(monthly_sorted)}")
    print(f"all_rows_deduped: {len(deduped)}")
    print(f"removed_duplicates: {len(monthly_sorted) - len(deduped)}")
    print(f"workbook: {WORKBOOK_PATH}")


if __name__ == "__main__":
    main()
