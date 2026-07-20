#!/usr/bin/env python3
"""
LNG Fleet Synthetic Data Generator
Generates 30 days of hyper-realistic operational data for all 10 vessels.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.generator import generate_and_save
import config.settings as cfg


def main():
    parser = argparse.ArgumentParser(
        description="LNG Fleet Synthetic Data Generator"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=cfg.DEFAULT_START_DATE.strftime("%Y-%m-%d"),
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=cfg.DEFAULT_NUM_DAYS,
        help="Number of days to generate",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "output"
        ),
        help="Output directory for CSV files",
    )
    parser.add_argument("--seed", type=int, default=cfg.RANDOM_SEED, help="Random seed")
    args = parser.parse_args()

    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid date format '{args.start_date}'. Use YYYY-MM-DD.")
        sys.exit(1)

    start_date = start_date.replace(tzinfo=timezone.utc)
    print(f"LNG Fleet Synthetic Data Generator")
    print(f"{'=' * 50}")
    print(f"Start date:  {start_date.strftime('%Y-%m-%d')}")
    print(f"Duration:    {args.days} days")
    print(f"Output dir:  {args.output}")
    print(f"Random seed: {args.seed}")
    print()

    t0 = time.time()
    summary, data = generate_and_save(
        output_dir=args.output,
        start_date=start_date,
        num_days=args.days,
    )
    elapsed = time.time() - t0

    cii_ratings = {}
    for c in data["cii"]:
        cii_ratings[c.cii_rating] = cii_ratings.get(c.cii_rating, 0) + 1

    vessels = data["vessels"]
    vessels_list = [f"{v.name} ({v.engine_type}, {v.capacity_m3}m³)" for v in vessels]

    print(f"{'=' * 50}")
    print(f"GENERATION COMPLETE — {elapsed:.1f}s")
    print(f"{'=' * 50}")
    print()
    print(f"{'Data Product':<30} {'Records':>10}")
    print(f"{'-' * 42}")
    for key, count in sorted(summary.items()):
        print(f"{key:<30} {count:>10,}")
    print(f"{'-' * 42}")
    print(f"{'Total records':<30} {sum(summary.values()):>10,}")
    print()
    print(f"CII Rating Distribution:")
    for rating in sorted(cii_ratings.keys()):
        print(f"  {rating}: {cii_ratings[rating]}")
    print()
    print(f"Vessels:")
    for v in vessels_list:
        print(f"  {v}")
    print()
    print(f"CSV Output Files:")
    output_dir = args.output
    for fname in sorted(os.listdir(output_dir)):
        if fname.endswith(".csv"):
            fpath = os.path.join(output_dir, fname)
            size_kb = os.path.getsize(fpath) / 1024
            print(f"  {fname:<35} {size_kb:>8.1f} KB")
    print()
    print(f"Output directory: {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    main()
