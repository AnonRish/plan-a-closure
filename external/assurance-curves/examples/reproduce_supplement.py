"""Recompute every number the Verification Plan's appendix / 2034 section states for random sampling."""
import math

import assurance_curves as ac
from assurance_curves import RogueDeploymentModel

rows = []
def check(label, stated, computed, tol):
    ok = abs(computed - stated) <= tol * abs(stated)
    rows.append((label, stated, computed, "ok" if ok else "MISMATCH"))

m = RogueDeploymentModel(budget=0.01, packet_size=100.0)          # 1 % budget, 100 H100e-hour packets
check("C * N_fake needed for 99 % (\"about 4.6\")", 4.6, ac.LN_100, 0.01)
check("H100e-hours of unapproved work to 99 % (\"~46,000\")", 46_000, m.h100e_hours_to_detect(0.99, model="poisson"), 0.01)
check("hours to catch a 10K H100e rogue deployment (\"~4.6 hours\")", 4.6, m.hours_to_detect(10_000, 0.99, model="poisson"), 0.01)
check("hours to catch a 1K H100e rogue deployment (\"~46 hours\")", 46, m.hours_to_detect(1_000, 0.99, model="poisson"), 0.01)

print(f"{'quantity':66} {'stated':>10} {'computed':>12}  check")
for label, st, co, ok in rows:
    print(f"{label:66} {st:>10g} {co:>12.5g}  {ok}")

print("\nWhat the supplement does not state (exact form vs its Poisson form, same inputs):")
ex = m.h100e_hours_to_detect(0.99); po = m.h100e_hours_to_detect(0.99, model="poisson")
print(f"  exact  : {ex:,.1f} H100e-hours ({ex/10_000:.4f} h at 10K H100e)   poisson: {po:,.1f} ({po/10_000:.4f} h)")
print(f"  a 63.4 % chance of catching a 10K H100e deployment within ONE hour: {m.p_detect(10_000, 1):.4f}")
print(f"  trusted recompute capacity implied by 1 % of a 33 B H100e pool: {m.recompute_capacity_h100e(33e9):,.0f} H100e")
print(f"  ... versus the whole 2029 world stock the same page declares:    {224e6+26e6+39e6:,.0f} H100e")
print("\nDetection time by tap granularity, 99 %, 1 % budget (Poisson form, hours):")
for r in ac.granularity_table(0.01, 0.99, [1_000, 10_000, 100_000]):
    print(f"  {r['granularity']:20} packet={r['packet_size_h100e_hours']:>6g} H100e-h   "
          f"1K: {r['hours_to_detect_1000_h100e']:>8.1f}   10K: {r['hours_to_detect_10000_h100e']:>7.1f}   100K: {r['hours_to_detect_100000_h100e']:>6.2f}")
