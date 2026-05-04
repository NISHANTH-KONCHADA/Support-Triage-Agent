"""
Command-line entry point for the Support Triage Agent batch workflow.

Usage:
    python code/main.py
"""

import csv
import time
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from agent import triage

ROOT = Path(__file__).parent.parent
REQUEST_DELAY_SECONDS = 2
OUTPUT_FIELDS = ["status", "product_area", "response", "justification", "request_type"]


def _find_input_csv() -> Path:
    candidates = [
        ROOT / "support_tickets" / "support_tickets.csv",
        ROOT / "support_tickets" / "support_issues.csv",
        ROOT / "support_issues" / "support_issues.csv",
        ROOT / "support_issues" / "support_tickets.csv",
    ]
    for path in candidates:
        if path.exists():
            return path

    for path in ROOT.rglob("support_*.csv"):
        if "sample" not in path.name and "output" not in path.name:
            return path

    raise FileNotFoundError("Could not find the support issues CSV.")


def _read_csv(path: Path):
    with path.open(encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))


def _count_done(output_csv: Path) -> int:
    if not output_csv.exists():
        return 0
    try:
        with output_csv.open(encoding="utf-8") as handle:
            return max(0, sum(1 for _ in handle) - 1)
    except Exception:
        return 0


def main() -> None:
    input_csv = _find_input_csv()
    output_csv = input_csv.parent / "output.csv"

    print(f"[Main] Input : {input_csv}", flush=True)
    print(f"[Main] Output: {output_csv}", flush=True)

    rows = _read_csv(input_csv)
    total = len(rows)
    print(f"[Main] {total} tickets to process\n", flush=True)

    if rows:
        print(f"[Main] Columns detected: {list(rows[0].keys())}\n", flush=True)

    already_done = _count_done(output_csv)
    if already_done:
        print(f"[Main] Resuming from ticket {already_done + 1}\n", flush=True)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if already_done else "w"

    with output_csv.open(mode, newline="", encoding="utf-8") as handle:
        original_keys = list(rows[0].keys()) if rows else []
        all_fields = original_keys + [field for field in OUTPUT_FIELDS if field not in original_keys]
        writer = csv.DictWriter(handle, fieldnames=all_fields, extrasaction="ignore")
        if not already_done:
            writer.writeheader()

        for index, row in enumerate(rows, 1):
            if index <= already_done:
                continue

            row_lower = {key.lower().strip(): value for key, value in row.items()}
            issue = row_lower.get("issue", "").strip()
            subject = row_lower.get("subject", "").strip()
            company = row_lower.get("company", "").strip()

            print(f"[{index}/{total}] company={company!r} | {(subject or issue)[:60]!r}", flush=True)

            started_at = time.time()
            result = triage(issue, subject, company)
            elapsed = time.time() - started_at

            print(
                f"  -> {result['status']} | {result['request_type']} "
                f"| {result['product_area']} ({elapsed:.1f}s)",
                flush=True,
            )

            writer.writerow({**row, **result})
            handle.flush()

            if index < total:
                time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\nDone. Output written to: {output_csv}", flush=True)


if __name__ == "__main__":
    main()
