from dataclasses import dataclass
from typing import List


@dataclass
class SPPInstance:
    m: int
    n: int
    costs: List[int]          # length n
    col_rows: List[List[int]] # col_rows[j] = rows covered by column j (0-based)


def parse_orlib_spp(path: str) -> SPPInstance:
    """
    OR-LIB SPP (nw*) formatına uygun parser:

      m n
      then for each column j=1..n:
        cost  k  r1 r2 ... rk      (rows are 1-based)

    We convert rows to 0-based.
    """
    with open(path, "r", encoding="utf-8") as f:
        tokens: List[str] = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            tokens.extend(line.split())

    it = iter(tokens)
    m = int(next(it))
    n = int(next(it))

    costs: List[int] = [0] * n
    col_rows: List[List[int]] = [[] for _ in range(n)]

    for j in range(n):
        c = int(next(it))
        k = int(next(it))
        rows = [int(next(it)) - 1 for _ in range(k)]
        costs[j] = c
        col_rows[j] = rows

    return SPPInstance(m=m, n=n, costs=costs, col_rows=col_rows)