#!/usr/bin/env python3
"""LNG Fleet Telemetry Data Generator

Generates high-frequency synthetic telemetry data for LNG carriers.
Data is physically consistent and correlated across all sensor channels.

Usage:
    python run.py                          # Default: 1 day, all vessels, CSV+SQLite
    python run.py --days 30                # 30 days of data
    python run.py --vessels LNG-001        # Single vessel
    python run.py --format csv parquet     # CSV and Parquet output
    python run.py --timestep 60            # 60-second intervals
"""
import os
import sys
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def progress_callback(pct, step, total, eta):
    bar_len = 40
    filled = int(bar_len * pct / 100)
    bar = "=" * filled + "-" * (bar_len - filled)
    mins, secs = divmod(int(eta), 60)
    hours, mins = divmod(mins, 60)
    eta_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
    sys.stdout.write(f"\r  [{bar}] {pct:5.1f}% | Step {step}/{total} | ETA {eta_str}")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(
        description="LNG Fleet Telemetry Data Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--days", type=float, default=1.0,
                        help="Duration in days (default: 1)")
    parser.add_argument("--vessels", nargs="*", default=None,
                        help="Vessel IDs to simulate (default: all)")
    parser.add_argument("--format", nargs="+", default=["csv", "sqlite"],
                        choices=["csv", "sqlite", "parquet"],
                        help="Output formats (default: csv sqlite)")
    parser.add_argument("--timestep", type=int, default=30,
                        help="Timestep in seconds (default: 30)")
    parser.add_argument("--output", type=str, default="output",
                        help="Output directory (default: output)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--config", type=str, default="config",
                        help="Config directory (default: config)")
    args = parser.parse_args()

    if args.seed is not None:
        import numpy as np
        np.random.seed(args.seed)

    print("=" * 60)
    print("  LNG Fleet Telemetry Data Generator")
    print("=" * 60)
    print(f"  Duration:  {args.days} days")
    print(f"  Timestep:  {args.timestep}s")
    print(f"  Vessels:   {args.vessels or 'all'}")
    print(f"  Output:    {args.output} ({', '.join(args.format)})")
    print(f"  Seed:      {args.seed or 'random'}")
    print()

    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.config)
    if not os.path.isdir(config_dir):
        print(f"Error: Config directory not found: {config_dir}")
        sys.exit(1)

    from simulator_engine import TelemetrySimulator
    sim = TelemetrySimulator(config_dir=config_dir)
    sim.timestep = args.timestep
    sim.gen_config["output"]["formats"] = args.format
    sim.gen_config["output"]["directory"] = args.output
    sim.buffer_size = 10000

    sim.initialize(vessel_ids=args.vessels)
    print(f"  Initialized {len(sim.vessels)} vessels")
    print()

    start = time.time()
    sim.run(duration_days=args.days, progress_callback=progress_callback)
    elapsed = time.time() - start

    print()
    print(f"  Wall time: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
