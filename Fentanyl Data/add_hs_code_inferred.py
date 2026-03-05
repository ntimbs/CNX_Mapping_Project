#!/usr/bin/env python3
"""
Add/refresh `hs_code_inferred` in the precursor workbook.

Inference order:
1) Use assigned HS6 from `hs_codes_unique_combined` when present.
2) Exact normalized name/alias match to rows with assigned HS6.
3) Fuzzy name match to known names.
4) Token-based vote from known names.
5) Keyword rule for fentanyl-family strings.
6) Global most-common HS6 fallback.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
import re

import pandas as pd


WORKBOOK_FILE = Path(__file__).resolve().parent / "Fentanyl_Precursor_List_Combined_with_schedule_dates.xlsx"
SHEET_NAME = "Sheet 1"
INFER_COL = "hs_code_inferred"
REASON_COL = "hs_code_inference_reason"

HS6_RE = re.compile(r"\b(\d{6})\b")
TOKEN_RE = re.compile(r"[a-z0-9]{4,}")
FENTANYL_HINT_RE = re.compile(r"(fentanyl|fentanil|carfentanil|norfentanyl)", re.IGNORECASE)


def normalize_name(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text.strip().lower())
    return text


def extract_primary_hs6(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    found = HS6_RE.findall(text)
    return found[0] if found else ""


def split_alt_names(value: object) -> list[str]:
    if pd.isna(value):
        return []
    text = str(value)
    parts = [p.strip() for p in text.split(";")]
    return [p for p in parts if p]


def infer_code(
    chemical_name: str,
    alt_names: list[str],
    name_to_codes: dict[str, Counter[str]],
    known_names: list[str],
    token_to_codes: dict[str, Counter[str]],
    fentanyl_mode_code: str,
    global_mode_code: str,
) -> tuple[str, str]:
    candidates = [chemical_name] + alt_names
    norm_candidates = [normalize_name(x) for x in candidates if normalize_name(x)]

    # Exact normalized match.
    exact_votes: Counter[str] = Counter()
    exact_hits: list[str] = []
    for name in norm_candidates:
        if name in name_to_codes:
            exact_votes.update(name_to_codes[name])
            exact_hits.append(name)
    if exact_votes:
        top_code, top_count = exact_votes.most_common(1)[0]
        matched = ", ".join(dict.fromkeys(exact_hits))[:180]
        reason = (
            f"Exact normalized name/alias match to known HS6 mapping "
            f"(matched: {matched}); selected {top_code} with top vote {top_count}."
        )
        return top_code, reason

    # Fuzzy match against known names.
    best_ratio = 0.0
    best_code = ""
    best_query = ""
    best_known = ""
    for query in norm_candidates:
        for known in known_names:
            ratio = SequenceMatcher(None, query, known).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_code = name_to_codes[known].most_common(1)[0][0]
                best_query = query
                best_known = known
    if best_ratio >= 0.88 and best_code:
        reason = (
            f"Fuzzy match to known name '{best_known}' from query '{best_query}' "
            f"(similarity {best_ratio:.3f}); selected {best_code}."
        )
        return best_code, reason

    # Token vote across known names.
    token_votes: Counter[str] = Counter()
    token_hits: list[str] = []
    for query in norm_candidates:
        for token in TOKEN_RE.findall(query):
            if token in token_to_codes:
                token_votes.update(token_to_codes[token])
                token_hits.append(token)
    if token_votes:
        top_code, top_count = token_votes.most_common(1)[0]
        tokens = ", ".join(sorted(set(token_hits)))[:180]
        reason = (
            f"Token-based vote from known HS6 mappings "
            f"(tokens: {tokens}); selected {top_code} with top vote {top_count}."
        )
        return top_code, reason

    # Keyword fallback for fentanyl-family names.
    raw_joined = " ".join(candidates)
    if FENTANYL_HINT_RE.search(raw_joined):
        reason = (
            f"Keyword fallback: fentanyl-family term detected; "
            f"used fentanyl-mode HS6 {fentanyl_mode_code}."
        )
        return fentanyl_mode_code, reason

    reason = f"Global fallback: no exact/fuzzy/token/keyword evidence; used global-mode HS6 {global_mode_code}."
    return global_mode_code, reason


def main() -> None:
    if not WORKBOOK_FILE.exists():
        raise FileNotFoundError(f"Workbook not found: {WORKBOOK_FILE}")

    df = pd.read_excel(WORKBOOK_FILE, sheet_name=SHEET_NAME)
    required = {"chemical_name_list", "hs_codes_unique_combined", "alt_names"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in workbook: {sorted(missing)}")

    # Build knowledge base from rows with assigned HS6.
    name_to_codes: dict[str, Counter[str]] = defaultdict(Counter)
    token_to_codes: dict[str, Counter[str]] = defaultdict(Counter)
    all_codes: list[str] = []
    fentanyl_codes: list[str] = []

    for _, row in df.iterrows():
        hs6 = extract_primary_hs6(row.get("hs_codes_unique_combined"))
        if not hs6:
            continue
        all_codes.append(hs6)

        names = [row.get("chemical_name_list")] + split_alt_names(row.get("alt_names"))
        for raw_name in names:
            norm = normalize_name(raw_name)
            if not norm:
                continue
            name_to_codes[norm][hs6] += 1
            for token in TOKEN_RE.findall(norm):
                token_to_codes[token][hs6] += 1
            if FENTANYL_HINT_RE.search(norm):
                fentanyl_codes.append(hs6)

    if not all_codes:
        raise ValueError("No HS6 values found in hs_codes_unique_combined to infer from.")

    global_mode_code = Counter(all_codes).most_common(1)[0][0]
    fentanyl_mode_code = Counter(fentanyl_codes).most_common(1)[0][0] if fentanyl_codes else global_mode_code
    known_names = list(name_to_codes.keys())

    inferred_codes: list[str] = []
    infer_reasons: list[str] = []
    for _, row in df.iterrows():
        assigned = extract_primary_hs6(row.get("hs_codes_unique_combined"))
        if assigned:
            inferred_codes.append(assigned)
            infer_reasons.append(
                f"Used assigned HS6 from hs_codes_unique_combined ({assigned}); no inference required."
            )
            continue

        chemical_name = "" if pd.isna(row.get("chemical_name_list")) else str(row.get("chemical_name_list"))
        alt_names = split_alt_names(row.get("alt_names"))
        code, reason = infer_code(
            chemical_name=chemical_name,
            alt_names=alt_names,
            name_to_codes=name_to_codes,
            known_names=known_names,
            token_to_codes=token_to_codes,
            fentanyl_mode_code=fentanyl_mode_code,
            global_mode_code=global_mode_code,
        )
        inferred_codes.append(code)
        infer_reasons.append(reason)

    df[INFER_COL] = inferred_codes
    df[REASON_COL] = infer_reasons

    with pd.ExcelWriter(WORKBOOK_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)

    print(f"Updated workbook: {WORKBOOK_FILE}")
    print(f"Rows: {len(df)}")
    print(f"{INFER_COL} non-empty count: {(df[INFER_COL].astype(str).str.strip() != '').sum()}")
    print(f"{REASON_COL} non-empty count: {(df[REASON_COL].astype(str).str.strip() != '').sum()}")
    print(f"Top inferred codes: {Counter(df[INFER_COL]).most_common(10)}")


if __name__ == "__main__":
    main()
