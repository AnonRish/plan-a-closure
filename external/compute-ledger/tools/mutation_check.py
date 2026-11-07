#!/usr/bin/env python3
"""Mutation check: inject one deliberate bug at a time and require the test suite to fail.

The real sources are never modified: each mutant lives in a temporary copy of src/, tests/ and pyproject.toml and is
imported through PYTHONPATH.  The unmutated copy must pass first, otherwise every mutant would be "killed" vacuously.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MUTANTS = [
    ("stock.py", "s = f * s + p", "s = f * (s + p)", "production also decays within its own year"),
    ("stock.py", "return 2.0 ** (-1.0 / half_life_years)", "return 2.0 ** (-1.0 * half_life_years)", "half-life used as a rate"),
    ("stock.py", "return (stock_next - production) / stock_t", "return (stock_next + production) / stock_t", "implied survival adds production"),
    ("stock.py", "if stock0 < 0 or any(p < 0 for p in production):", "if stock0 < 0:", "negative production accepted"),
    ("ledger.py", "if self._bal.get(ev.frm, 0.0) < amt:\n                raise LedgerError(\"retiring", "if self._bal.get(ev.frm, 0.0) <= amt:\n                raise LedgerError(\"retiring", "cannot retire an entire balance"),
    ("ledger.py", "            self._bal[ev.frm] -= amt\n            self._bal[ev.to] = self._bal.get(ev.to, 0.0) + amt", "            self._bal[ev.to] = self._bal.get(ev.to, 0.0) + amt", "transfer does not debit the source"),
    ("ledger.py", "            self.produced += amt", "            pass", "production not counted"),
    ("ledger.py", "            del self.history[n:]", "            pass", "failed post_all leaves history behind"),
    ("ledger.py", "if abs(self.conservation_error()) > tol * scale:", "if abs(self.conservation_error()) > 1e9 * scale:", "conservation check never fires"),
    ("ledger.py", "if not (amt > 0) or amt != amt or amt == float(\"inf\"):", "if not (amt > 0) or amt != amt:", "infinite amounts accepted"),
    ("distributions.py", "self.sigma_lo = math.log(self.p50 / self.p10) / Z90", "self.sigma_lo = math.log(self.p90 / self.p50) / Z90", "lower sigma from the upper quantile"),
    ("distributions.py", "math.exp(lo * lo / 2) * _N.cdf(-lo)", "math.exp(lo * lo / 2) * _N.cdf(lo)", "mean: wrong tail weight"),
    ("distributions.py", "        s = self.sigma_lo if p < 0.5 else self.sigma_hi\n        return self.p50 * math.exp(s * _N.inv_cdf(p))", "        s = self.sigma_hi if p < 0.5 else self.sigma_lo\n        return self.p50 * math.exp(s * _N.inv_cdf(p))", "ppf uses the wrong sigma per side"),
    ("distributions.py", "return _N.pdf(math.log(x / self.p50) / s) / (x * s)", "return _N.pdf(math.log(x / self.p50) / s) / s", "density without the 1/x Jacobian"),
    ("reconcile.py", "return (self.hi - self.lo) / (2 * _N.inv_cdf(0.5 + self.level / 2))", "return (self.hi - self.lo) / (2 * _N.inv_cdf(self.level))", "sigma from the wrong quantile"),
    ("reconcile.py", "hmax = max(m, 0.0) + 12 * s", "hmax = m + 12 * s", "grid bound ignores a negative likelihood centre"),
    ("reconcile.py", "m = estimate.center - declared ", "m = declared - estimate.center ", "likelihood centred on the wrong side"),
    ("reconcile.py", "return Consistency(z, 1.0 - _N.cdf(z))", "return Consistency(z, _N.cdf(z))", "one-sided p-value inverted"),
    ("reconcile.py", "t = 0.0 if c1 == c0 else (p - c0) / (c1 - c0)", "t = 0.0 if c1 == c0 else (p - c0) / (c1 + c0)", "quantile interpolation wrong"),
    ("reconcile.py", "return Posterior(grid, [x / total for x in w], [c / total for c in cum])", "return Posterior(grid, [x for x in w], [c / total for c in cum])", "pdf left unnormalised"),
    ("reconcile.py", "return [totals[min(n - 1, int(q * n))] for q in qs]", "return [totals[min(n - 1, int(q * n) // 2)] for q in qs]", "sum quantiles index halved"),
    ("planA.py", "tol = hw * coeff + hw + 0.2e6", "tol = 0.0", "no tolerance on the world-stock check"),
    ("planA.py", "\"US\": rest * o[\"us_share_of_non_china\"]", "\"US\": rest * (1 - o[\"us_share_of_non_china\"])", "US and RoW shares swapped"),
    ("planA.py", "within = abs(self.computed - self.published) <= self.tol", "within = abs(self.computed - self.published) < self.tol", "exact checks fail on equality"),
    ("planA.py", "return within if self.expect_match else not within", "return within", "negative check treated as positive"),
    ("planA.py", "return 0.5 * 10 ** (-decimals)", "return 10 ** (-decimals)", "printed precision doubled"),
]

EQUIVALENT = [
    ("ledger.py", "_undo(bal, reversed(self.history))", "_undo(bal, self.history)",
     "undo order: each undo is a plain additive adjustment, so the result does not depend on the order"),
]


def make_tree(fname=None, old=None, new=None) -> str:
    tmp = tempfile.mkdtemp(prefix="cl-mutant-")
    for d in ("src", "tests"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d), ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    shutil.copy(os.path.join(ROOT, "pyproject.toml"), tmp)
    if fname:
        path = os.path.join(tmp, "src", "compute_ledger", fname)
        text = open(path).read()
        if text.count(old) != 1:
            raise SystemExit("BAD MUTANT (pattern found %d times): %s: %s" % (text.count(old), fname, old[:60]))
        open(path, "w").write(text.replace(old, new))
    return tmp


def passes(tree: str) -> bool:
    env = dict(os.environ, PYTHONPATH=os.path.join(tree, "src"))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], cwd=tree, capture_output=True,
                       text=True, env=env, timeout=300)
    return r.returncode == 0


def main() -> int:
    base = make_tree()
    try:
        if not passes(base):
            print("the UNMUTATED copy fails the tests; every mutant would be 'killed' vacuously")
            return 2
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print("unmutated copy passes")
    survived, t0 = [], time.time()
    for fname, old, new, why in MUTANTS:
        tree = make_tree(fname, old, new)
        try:
            killed = not passes(tree)
        except subprocess.TimeoutExpired:
            killed = True
        finally:
            shutil.rmtree(tree, ignore_errors=True)
        print("%-9s %-16s %s" % ("killed" if killed else "SURVIVED", fname, why), flush=True)
        if not killed:
            survived.append(why)
    bad_equiv = []
    for fname, old, new, why in EQUIVALENT:
        tree = make_tree(fname, old, new)
        try:
            same = passes(tree)
        finally:
            shutil.rmtree(tree, ignore_errors=True)
        print("%-10s %-15s %s" % ("equivalent" if same else "NOT-EQUIV", fname, why), flush=True)
        if not same:
            bad_equiv.append(why)
    print("\n%d mutants, %d killed, %d survived (%.0fs); %d claimed-equivalent checked, %d wrongly claimed" % (
        len(MUTANTS), len(MUTANTS) - len(survived), len(survived), time.time() - t0, len(EQUIVALENT), len(bad_equiv)))
    return 1 if (survived or bad_equiv) else 0


if __name__ == "__main__":
    sys.exit(main())
