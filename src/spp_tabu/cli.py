import argparse
from pathlib import Path
from typing import List

from .parser import parse_orlib_spp
from .tabu import TabuSearchSPP


def _resolve_instance_path(raw_path: str) -> Path:
    p = Path(raw_path).expanduser()
    candidates: List[Path] = [p]

    # Common typo: "/data/foo" instead of "data/foo" from project root.
    if p.is_absolute():
        candidates.append(Path.cwd() / str(p).lstrip("/"))
    else:
        candidates.append(Path.cwd() / p)

    # Common file naming: omitted ".txt".
    for c in list(candidates):
        if c.suffix == "":
            candidates.append(c.with_suffix(".txt"))

    seen = set()
    deduped: List[Path] = []
    for c in candidates:
        key = str(c)
        if key not in seen:
            deduped.append(c)
            seen.add(key)

    for c in deduped:
        if c.is_file():
            return c

    attempted = ", ".join(str(c) for c in deduped)
    raise FileNotFoundError(
        f"Instance file not found. Tried: {attempted}. "
        f"If your file is in this repo, try: --instance data/sppnw01.txt"
    )


def main() -> None:
    p = argparse.ArgumentParser(prog="spp-tabu")
    p.add_argument("--instance", required=True, help="Path to OR-LIB SPP instance file")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--time", type=float, default=10.0, help="Time limit in seconds")
    p.add_argument("--iters", type=int, default=200_000)
    args = p.parse_args()

    try:
        instance_path = _resolve_instance_path(args.instance)
    except FileNotFoundError as e:
        raise SystemExit(str(e)) from e

    inst = parse_orlib_spp(str(instance_path))
    ts = TabuSearchSPP(inst, seed=args.seed, time_limit_s=args.time, max_iters=args.iters)
    x, best_cost = ts.solve()

    selected = sum(x)
    if best_cost is None:
        print(f"No feasible solution found. Selected cols={selected}")
    else:
        print(f"Best feasible cost={best_cost} | selected cols={selected}")


if __name__ == "__main__":
    main()
