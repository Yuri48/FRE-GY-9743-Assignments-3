"""Numbers behind the written bond-future answers (hw3_bond_future_answers.pdf).

Conventions: semi-annual coupons, 3M to delivery = tau = 0.25 (money-market
simple repo interest), accrued interest linear in the coupon period, prices per
100 face. Run with the project venv: .venv/bin/python hw3_bond_future_numbers.py
"""

import numpy as np
import pandas as pd

TAU = 0.25           # 3 months to delivery
NOTIONAL_YIELD = 0.06


def dirty_price(coupon: float, years: float, y: float) -> float:
    """Dirty price per 100 at yield y (semi-annual), `years` to maturity (may be off-cycle)."""
    n_full = int(np.floor(years * 2 + 1e-12))          # whole half-years after the next coupon
    frac = years * 2 - n_full                          # fraction of a period to the next coupon
    if frac < 1e-12:                                   # on a coupon date: next coupon a full period away
        n_full -= 1
        frac = 1.0
    times = frac + np.arange(n_full + 1)               # in half-years
    cfs = np.full(n_full + 1, 100 * coupon / 2)
    cfs[-1] += 100
    return float(np.sum(cfs / (1 + y / 2) ** times))


def accrued(coupon: float, years: float) -> float:
    frac_to_next = (years * 2) % 1
    elapsed = 0.0 if frac_to_next < 1e-12 else 1 - frac_to_next
    return 100 * coupon / 2 * elapsed


def clean_price(coupon: float, years: float, y: float) -> float:
    return dirty_price(coupon, years, y) - accrued(coupon, years)


def conversion_factor(coupon: float, years: float) -> float:
    """Assignment definition: clean price at a flat 6% yield, divided by 100."""
    return clean_price(coupon, years, NOTIONAL_YIELD) / 100


def clean_forward(coupon: float, years: float, spot_clean: float, repo: float, tau: float = TAU) -> float:
    """Clean forward price for delivery in tau years; assumes no coupon before delivery."""
    assert (years * 2) % 1 < 1e-12 or (years * 2) % 1 >= tau * 2 - 1e-12, "coupon before delivery"
    spot_dirty = spot_clean + accrued(coupon, years)
    return spot_dirty * (1 + repo * tau) - accrued(coupon, years - tau)


def implied_repo(fut: float, k: float, coupon: float, years: float, spot_clean: float,
                 tau: float = TAU) -> float:
    """Repo that makes the clean forward / K equal the futures price (no coupon before delivery)."""
    spot_dirty = spot_clean + accrued(coupon, years)
    invoice = fut * k + accrued(coupon, years - tau)
    return (invoice / spot_dirty - 1) / tau


def question_1_and_2() -> None:
    c, T, S, r = 0.04, 9.0, 100.0, 0.02
    ai_0, ai_d = accrued(c, T), accrued(c, T - TAU)
    bf_dirty = (S + ai_0) * (1 + r * TAU)
    bf = clean_forward(c, T, S, r)
    k = conversion_factor(c, T)
    k_delivery = conversion_factor(c, T - TAU)           # CME-style: measured at delivery
    print("Question 1")
    print(f"  accrued today = {ai_0:.4f}, accrued at delivery = {ai_d:.4f}")
    print(f"  dirty forward = {bf_dirty:.4f}, clean forward BF = {bf:.4f}")
    print(f"  K (9.00y, assignment definition) = {k:.6f}")
    print(f"  BF / K = {bf / k:.4f}")
    print(f"  dirty-forward / K (wrong: mixes accrued in) = {bf_dirty / k:.4f}")
    print(f"  K measured at delivery (8.75y) = {k_delivery:.6f}, BF / K = {bf / k_delivery:.4f}")

    fut = 115.3670
    r_imp = implied_repo(fut, k, c, T, S)
    print("Question 2.1")
    print(f"  invoice at delivery F*K + AI = {fut * k + ai_d:.4f}")
    print(f"  implied repo = {r_imp:.6%}")
    print(f"  d r_imp / d F = {k / ((S + ai_0) * TAU):.4%} per 1.00 of futures price,"
          f" {k / ((S + ai_0) * TAU) / 32 * 1e4:.2f} bp per 1/32")


# Hypothetical deliverable basket for the scenario analysis (Question 3).
BASKET = pd.DataFrame(
    {"coupon": [0.0575, 0.04, 0.02], "years": [7.0, 9.0, 10.0]},
    index=["A 5.75% 7y", "B 4.00% 9y", "C 2.00% 10y"],
)


def basket_table(y: float, repo: float, slope_bp_per_year: float = 0.0, pivot: float = 9.0) -> pd.DataFrame:
    rows = []
    for name, b in BASKET.iterrows():
        y_b = y + slope_bp_per_year * 1e-4 * (b.years - pivot)
        s = clean_price(b.coupon, b.years, y_b)
        k = conversion_factor(b.coupon, b.years)
        bf = clean_forward(b.coupon, b.years, s, repo)
        rows.append({"bond": name, "yield": y_b, "spot": s, "K": k, "BF": bf, "BF/K": bf / k})
    return pd.DataFrame(rows).set_index("bond")


def modified_duration(coupon: float, years: float, y: float, bump: float = 1e-5) -> float:
    up, down = dirty_price(coupon, years, y + bump), dirty_price(coupon, years, y - bump)
    return (down - up) / (2 * bump * dirty_price(coupon, years, y))


def question_3() -> None:
    repo = 0.02
    print("Question 3")
    t = basket_table(0.06, repo)
    print("  at a flat 6% yield every spot clean price / K is", (t["spot"] / t["K"]).round(6).unique())
    print("  modified duration at 4%:",
          {n: round(modified_duration(b.coupon, b.years, 0.04), 2) for n, b in BASKET.iterrows()})
    print("  K:", t["K"].round(4).to_dict())

    print("(a) BF/K across flat yield levels, repo 2%")
    grid = pd.DataFrame({f"{y:.0%}": basket_table(y, repo)["BF/K"] for y in [0.03, 0.04, 0.05, 0.06, 0.07, 0.08]})
    print(grid.round(3).to_string())
    print("  CTD:", grid.idxmin().to_dict())
    ys = np.linspace(0.03, 0.09, 6001)
    ctd = [basket_table(y, repo)["BF/K"].idxmin() for y in ys]
    for i in range(1, len(ys)):
        if ctd[i] != ctd[i - 1]:
            print(f"  CTD switches from {ctd[i - 1]} to {ctd[i]} at a flat yield of {ys[i]:.2%}")

    print("(b) Implied repo of every bond at the futures price F = min BF/K (flat 6.25%, repo 2%)")
    t = basket_table(0.0625, repo)
    fut = t["BF/K"].min()
    for name, b in BASKET.iterrows():
        r_imp = implied_repo(fut, t.loc[name, "K"], b.coupon, b.years, t.loc[name, "spot"])
        print(f"  {name}: BF/K={t.loc[name, 'BF/K']:.3f}  implied repo={r_imp:.3%}")

    print("(c) Curve twists around the 9y point, level 6.25%, repo 2%")
    for slope in [-10, -5, 0, 5, 10]:
        t = basket_table(0.0625, repo, slope)
        print(f"  slope {slope:+3d} bp/yr: " + "  ".join(f"{n}={v:.3f}" for n, v in t["BF/K"].items())
              + f"  -> CTD {t['BF/K'].idxmin()}")
    print("    same twists at a 4% level:",
          {s: basket_table(0.04, repo, s)["BF/K"].idxmin() for s in [-10, 10, 25]})


if __name__ == "__main__":
    question_1_and_2()
    question_3()
