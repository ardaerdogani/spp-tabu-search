import argparse
import glob
import statistics as st

from spp_tabu.parser import parse_orlib_spp
from spp_tabu.tabu import TabuSearchSPP


def run_one(path: str, seeds: int, time_limit: float):
    inst = parse_orlib_spp(path)
    costs = []
    feas = 0
    for s in range(seeds):
        ts = TabuSearchSPP(inst, seed=s, time_limit_s=time_limit)
        _, c = ts.solve()
        if c is not None:
            feas += 1
            costs.append(c)
    return {
        "instance": path,
        "feas_rate": feas / seeds,
        "best": min(costs) if costs else None,
        "avg": st.mean(costs) if costs else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", required=True, help="Glob pattern, e.g. data/*.txt")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--time", type=float, default=10.0)
    args = ap.parse_args()

    for path in sorted(glob.glob(args.pattern)):
        r = run_one(path, args.seeds, args.time)
        print(r)


if __name__ == "__main__":
    main()