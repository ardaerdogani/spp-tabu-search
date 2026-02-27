import random
import time
from typing import List, Tuple, Optional, Set

from .parser import SPPInstance


class TabuSearchSPP:
    def __init__(
        self,
        inst: SPPInstance,
        seed: int = 0,
        base_tenure: int = 10,
        tenure_rand: int = 10,
        max_iters: int = 200_000,
        time_limit_s: float = 10.0,
        stall_limit: int = 20_000,
        cand_mult: int = 30,
    ):
        self.seed = seed
        self.rng = random.Random(seed)
        self.I = inst
        self.base_tenure = base_tenure
        self.tenure_rand = tenure_rand
        self.max_iters = max_iters
        self.time_limit_s = time_limit_s
        self.stall_limit = stall_limit
        self.cand_mult = cand_mult

        self.x = [0] * self.I.n
        self.cover = [0] * self.I.m
        self.cost = 0

        self.tabu_until = [-1] * self.I.n
        self.lam = 10.0

        self.best_feas_x: Optional[List[int]] = None
        self.best_feas_cost: float = float("inf")

        self._row_cols: Optional[List[List[int]]] = None
        self._col_masks: Optional[List[int]] = None

    def infeas(self) -> int:
        return sum(abs(c - 1) for c in self.cover)

    def obj(self) -> float:
        return self.cost + self.lam * self.infeas()

    def _apply_flip(self, j: int) -> None:
        if self.x[j] == 0:
            self.x[j] = 1
            self.cost += self.I.costs[j]
            for i in self.I.col_rows[j]:
                self.cover[i] += 1
        else:
            self.x[j] = 0
            self.cost -= self.I.costs[j]
            for i in self.I.col_rows[j]:
                self.cover[i] -= 1

    def _delta_flip(self, j: int) -> Tuple[int, int]:
        add = (self.x[j] == 0)
        dcost = self.I.costs[j] if add else -self.I.costs[j]

        dinf = 0
        for i in self.I.col_rows[j]:
            before = abs(self.cover[i] - 1)
            after_cov = self.cover[i] + (1 if add else -1)
            after = abs(after_cov - 1)
            dinf += (after - before)
        return dcost, dinf

    def _ensure_row_index(self) -> None:
        if self._row_cols is not None:
            return
        row_cols = [[] for _ in range(self.I.m)]
        for j in range(self.I.n):
            for i in self.I.col_rows[j]:
                row_cols[i].append(j)
        self._row_cols = row_cols

    def _ensure_col_masks(self) -> None:
        if self._col_masks is not None:
            return
        col_masks: List[int] = [0] * self.I.n
        for j, rows in enumerate(self.I.col_rows):
            mask = 0
            for i in rows:
                mask |= (1 << i)
            col_masks[j] = mask
        self._col_masks = col_masks

    def _initial_solution_randomized(self, deadline: float) -> None:
        if time.time() >= deadline:
            return

        self._ensure_row_index()
        self._ensure_col_masks()
        assert self._row_cols is not None
        assert self._col_masks is not None

        all_rows_mask = (1 << self.I.m) - 1
        best_inf = self.infeas()
        best_x = self.x[:]
        best_cover = self.cover[:]
        best_cost = self.cost

        attempt = 0
        while time.time() < deadline:
            arng = random.Random(self.seed + attempt)
            attempt += 1

            x = [0] * self.I.n
            cover = [0] * self.I.m
            cost = 0
            covered_mask = 0

            while covered_mask != all_rows_mask and time.time() < deadline:
                uncovered_rows = [
                    i for i in range(self.I.m)
                    if ((covered_mask >> i) & 1) == 0
                ]
                if not uncovered_rows:
                    break

                i = uncovered_rows[arng.randrange(len(uncovered_rows))]
                not_covered_mask = all_rows_mask ^ covered_mask

                best_overlap = None
                scored: List[Tuple[int, int, int]] = []
                for j in self._row_cols[i]:
                    if x[j] == 1:
                        continue

                    mask = self._col_masks[j]
                    overlap = (mask & covered_mask).bit_count()
                    new_cov = (mask & not_covered_mask).bit_count()

                    if (best_overlap is None) or (overlap < best_overlap):
                        best_overlap = overlap
                        scored = [(self.I.costs[j], -new_cov, j)]
                    elif overlap == best_overlap:
                        scored.append((self.I.costs[j], -new_cov, j))

                if not scored:
                    break

                scored.sort()
                top = min(30, len(scored))
                _, _, chosen = scored[arng.randrange(top)]

                x[chosen] = 1
                cost += self.I.costs[chosen]
                for r in self.I.col_rows[chosen]:
                    cover[r] += 1
                covered_mask |= self._col_masks[chosen]

            inf = sum(abs(c - 1) for c in cover)
            if inf < best_inf:
                best_inf = inf
                best_x = x
                best_cover = cover
                best_cost = cost
                if inf == 0:
                    break

        self.x = best_x
        self.cover = best_cover
        self.cost = best_cost

    def _initial_solution_greedy(self, deadline: Optional[float] = None) -> None:
        if deadline is None:
            deadline = time.time()

        self._initial_solution_randomized(deadline)
        if self.infeas() == 0 or time.time() >= deadline:
            return

        self._ensure_row_index()
        assert self._row_cols is not None

        # Fix uncovered rows by adding a cheap column covering them
        uncovered = {i for i in range(self.I.m) if self.cover[i] == 0}
        while uncovered and time.time() < deadline:
            i = next(iter(uncovered))
            best_j = None
            best_score = float("inf")

            for j in self._row_cols[i]:
                if self.x[j] == 1:
                    continue
                gain = sum(1 for r in self.I.col_rows[j] if self.cover[r] == 0)
                score = self.I.costs[j] / max(1, gain)
                if score < best_score:
                    best_score, best_j = score, j

            if best_j is None:
                if self._row_cols[i]:
                    best_j = self.rng.choice(self._row_cols[i])
                else:
                    best_j = self.rng.randrange(self.I.n)

            self._apply_flip(best_j)
            uncovered = {i for i in range(self.I.m) if self.cover[i] == 0}

        # Cleanup: drop only redundant columns while keeping exact coverage feasible.
        for _ in range(2):
            improved = True
            while improved and time.time() < deadline:
                improved = False
                for j in range(self.I.n):
                    if self.x[j] == 1:
                        dcost, dinf = self._delta_flip(j)
                        if dinf == 0 and dcost < 0:
                            self._apply_flip(j)
                            improved = True

    def _candidate_columns(self) -> List[int]:
        violated = [i for i, c in enumerate(self.cover) if c != 1]
        if not violated:
            k = min(self.I.n, max(200, self.I.n // 10))
            return self.rng.sample(range(self.I.n), k)

        self._ensure_row_index()
        assert self._row_cols is not None

        cols: Set[int] = set()
        for i in violated:
            cols.update(self._row_cols[i])

        cols = list(cols)
        try:
            mult = int(self.cand_mult)
        except (TypeError, ValueError):
            mult = 0

        cap = max(0, min(self.I.n, len(cols), mult * (len(violated) + 1)))
        if len(cols) > cap:
            cols = self.rng.sample(cols, cap)
        return cols

    def solve(self) -> Tuple[List[int], Optional[int]]:
        start = time.time()
        init_deadline = start + max(0.0, self.time_limit_s)
        self._initial_solution_greedy(init_deadline)

        if self.infeas() == 0 and self.cost < self.best_feas_cost:
            self.best_feas_cost = self.cost
            self.best_feas_x = self.x[:]

        best_overall = self.obj()
        best_overall_x = self.x[:]
        stall = 0

        for it in range(self.max_iters):
            if time.time() - start >= self.time_limit_s:
                break

            inf = self.infeas()
            if inf == 0:
                if self.cost < self.best_feas_cost:
                    self.best_feas_cost = self.cost
                    self.best_feas_x = self.x[:]
                    stall = 0
                else:
                    stall += 1
                self.lam = max(1.0, self.lam * 0.995)
            else:
                stall += 1
                self.lam = min(10_000.0, self.lam * 1.005)

            if stall >= self.stall_limit:
                for _ in range(5):
                    j = self.rng.randrange(self.I.n)
                    self._apply_flip(j)
                stall = 0

            cand = self._candidate_columns()

            best_move = None
            best_move_val = float("inf")
            cur_obj = self.obj()

            for j in cand:
                dcost, dinf = self._delta_flip(j)
                new_obj = cur_obj + dcost + self.lam * dinf

                is_tabu = (self.tabu_until[j] > it)
                aspiration = False

                if self.best_feas_x is not None:
                    if (inf + dinf) == 0 and (self.cost + dcost) < self.best_feas_cost:
                        aspiration = True
                if new_obj < best_overall:
                    aspiration = True

                if is_tabu and not aspiration:
                    continue

                if new_obj < best_move_val:
                    best_move_val = new_obj
                    best_move = j

            if best_move is None:
                best_move = self.rng.randrange(self.I.n)

            self._apply_flip(best_move)

            tenure = self.base_tenure + self.rng.randint(0, self.tenure_rand)
            self.tabu_until[best_move] = it + tenure

            new_obj = self.obj()
            if new_obj < best_overall:
                best_overall = new_obj
                best_overall_x = self.x[:]
                stall = 0

        if self.best_feas_x is not None:
            return self.best_feas_x, int(self.best_feas_cost)
        return best_overall_x, None
