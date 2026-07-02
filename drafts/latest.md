## Verdict
Vol-selling crowding at cycle extremes — **add convexity now**, cut any residual short-vol carry exposure to zero before Q3 2025 event cluster hits.

---

## Trades

1. **Long SPX 3M 5% OTM puts** — 40bps NAV; max loss = premium paid; roll monthly if VIX stays <15
2. **Long VIX call spreads 18/28** Jun-Sep expiry — 25bps NAV; defined loss = spread premium ~15bps
3. **Short 1M realized vol vs. long 3M implied vol (VIX/VVIX ratio trade)** — 30bps NAV; stop if VVIX drops below 85 for 5 consecutive days
4. **Long UVXY vs. short XIV-proxy ETF pair** — 20bps NAV; size for 2:1 convexity; exit if VIX term structure steepens >3pts front-to-back
5. **Tail hedge via SRVIX swaption straddles** — 15bps NAV; captures rates-equity vol correlation breakdown

---

## Triggers

| Signal | Level | Action |
|---|---|---|
| CBOE Skew Index | >145 sustained 3 days | Add 15bps to put position; trim VIX call spreads |
| VIX spot | <13 | Double put ladder; initiate VVIX calls |
| CTAs net short vol exposure | >2 SD above 5Y mean | Add 20bps across all legs; full conviction sizing |
| SPX 1M realized vol | <10 for 10 days | Trigger trade 3; ratio vol carry unwind imminent |
| VVIX/VIX ratio | >6.5 | Exit all short-vol hedges; rotate to pure long convexity only |

---

## Thesis

- **Crowding is structural, not cyclical.** 0DTE volume now >50% of SPX options flow (2023-2024); systematic vol sellers — risk parity, target-vol funds, dispersion desks — have compressed realized vol to levels last seen pre-Feb 2018 and pre-Aug 2024. Both episodes produced 30-40% VIX spikes within 5 trading days of crowding peaks.

- **Carry is priced for perfection, not probability.** VRP (implied minus realized) running 4-6 vol points — top decile since 2010. When VRP compresses this far, mean-reversion events are larger and faster; Aug 2024 unwind saw VIX +180% in 72 hours from an identical setup. CFTC non-commercial and Goldman flow data show net short vol at 18-month highs entering 2025.

- **Macro event density creates ignition risk.** Q2-Q3 2025 stacks Fed pivot uncertainty, debt ceiling resolution, election-cycle policy volatility, and geopolitical optionality. Systematic strategies have no discretionary override — forced unwinds are mechanical and simultaneous, amplifying moves 2-3x versus discretionary-driven selloffs (March 2020, Feb 2018, Aug 2024 all confirm).

---

## Invalidation

1. **Crowding already unwound:** CFTC non-commercial net short vol drops below 1-year average AND 0DTE share of volume falls below 40% — exit all convexity positions within 2 sessions; thesis is structurally broken.

2. **Vol regime organically elevated:** SPX 1M realized vol rises above 18 without a spike event AND VIX term structure inverts front-to-back by >4pts for 10+ consecutive days — carry is already dead; close positions, premium bleed is unjustified.

3. **Macro catalysts resolve cleanly:** Debt ceiling cleared before June 2025, Fed delivers unambiguous forward guidance, geopolitical risk premium collapses simultaneously — reduce all tail hedges to a 50bps NAV maintenance floor and watch for re-entry.