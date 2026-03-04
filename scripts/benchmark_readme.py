from __future__ import annotations

import argparse
import csv
import statistics as st
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from spp_tabu.parser import parse_orlib_spp
from spp_tabu.tabu import TabuSearchSPP


def _format_time(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def _format_maybe_number(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"{value:g}"


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def run_one(instance_path: Path, seeds: int, time_limit: float) -> dict[str, str]:
    inst = parse_orlib_spp(str(instance_path))
    costs: list[int] = []
    feasible = 0

    for seed in range(seeds):
        _, cost = TabuSearchSPP(inst, seed=seed, time_limit_s=time_limit).solve()
        if cost is not None:
            feasible += 1
            costs.append(cost)

    avg_cost = st.mean(costs) if costs else None
    return {
        "instance": _display_path(instance_path),
        "time_s": _format_time(time_limit),
        "seeds": str(seeds),
        "feas_rate": f"{feasible / seeds:.1f}",
        "best_cost": _format_maybe_number(min(costs) if costs else None),
        "avg_cost": _format_maybe_number(avg_cost),
    }


def write_csv(rows: Iterable[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["instance", "time_s", "seeds", "feas_rate", "best_cost", "avg_cost"]
    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_svg(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width = 760
    height = 420
    left = 90
    right = 40
    top = 70
    bottom = 80
    chart_width = width - left - right
    chart_height = height - top - bottom
    bars = len(rows)
    bar_step = chart_width / max(1, bars)
    bar_width = min(90, bar_step * 0.58)
    axis_bottom = top + chart_height
    tick_values = [0.0, 0.25, 0.5, 0.75, 1.0]
    caption = f"Seeds: 0-{int(rows[0]['seeds']) - 1}" if rows else "Seeds: none"

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" '
            'aria-labelledby="title desc">'
        ),
        '  <title id="title">sppnw01 feasibility rate vs time budget</title>',
        '  <desc id="desc">Bar chart showing the feasibility rate for time budgets 1, 3, 5, and 10 seconds.</desc>',
        '  <rect width="100%" height="100%" fill="#fffdf8"/>',
        '  <text x="380" y="34" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="20" fill="#1f2933">sppnw01 feasibility rate vs time budget</text>',
        '  <text x="380" y="56" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#52606d">Feasibility rate across 5 seeds for the bundled OR-LIB instance</text>',
        f'  <line x1="{left}" y1="{axis_bottom}" x2="{width - right}" y2="{axis_bottom}" stroke="#1f2933" stroke-width="2"/>',
        f'  <line x1="{left}" y1="{top}" x2="{left}" y2="{axis_bottom}" stroke="#1f2933" stroke-width="2"/>',
    ]

    for tick in tick_values:
        y = axis_bottom - chart_height * tick
        parts.append(f'  <line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#d9e2ec" stroke-width="1"/>')
        parts.append(
            f'  <text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" '
            'font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#52606d">'
            f'{tick:.2f}</text>'
        )

    for idx, row in enumerate(rows):
        value = float(row["feas_rate"])
        x = left + idx * bar_step + (bar_step - bar_width) / 2
        bar_height = chart_height * value
        y = axis_bottom - bar_height
        parts.extend(
            [
                f'  <rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="8" fill="#1f7a8c"/>',
                f'  <text x="{x + bar_width / 2:.1f}" y="{axis_bottom + 24}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#1f2933">{row["time_s"]}s</text>',
                f'  <text x="{x + bar_width / 2:.1f}" y="{max(top + 16, y - 10):.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#102a43">{value:.1f}</text>',
            ]
        )

    parts.extend(
        [
            f'  <text x="{left - 55}" y="{top - 16}" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#52606d">feasibility</text>',
            f'  <text x="{left + chart_width / 2:.1f}" y="{height - 18}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#52606d">Time budget (seconds)</text>',
            f'  <text x="380" y="{height - 38}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#52606d">{caption}</text>',
            '</svg>',
        ]
    )

    output_path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate README benchmark artifacts.")
    parser.add_argument("--instance", required=True, help="Path to the benchmark instance file.")
    parser.add_argument("--times", type=float, nargs="+", required=True, help="Time budgets in seconds.")
    parser.add_argument("--seeds", type=int, default=5, help="Number of seeds to evaluate, starting from 0.")
    parser.add_argument("--csv-out", required=True, help="Path to the output CSV file.")
    parser.add_argument("--svg-out", required=True, help="Path to the output SVG file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instance_path = Path(args.instance)
    csv_path = Path(args.csv_out)
    svg_path = Path(args.svg_out)

    # Run longer budgets first to reduce the chance that earlier short runs skew
    # later time-limited measurements on a busy machine. Results are written back
    # in ascending order for readability.
    measured = [
        run_one(instance_path, args.seeds, time_limit)
        for time_limit in sorted(args.times, reverse=True)
    ]
    rows = sorted(measured, key=lambda row: float(row["time_s"]))
    write_csv(rows, csv_path)
    write_svg(rows, svg_path)

    print(f"Wrote {csv_path}")
    print(f"Wrote {svg_path}")


if __name__ == "__main__":
    main()
