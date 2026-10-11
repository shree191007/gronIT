# gronIT

Antarctic Neocloud: an ecology-constrained subsea AI compute network in the Southern Ocean. This repo holds the
numbers behind the ideathon pitch.

| Folder | What it is |
|---|---|
| `simulator/` | Interactive 1 MW pod flow simulator (single HTML page; lattice-Boltzmann heat flow, coolant loop, throttling, data and power path). `python build.py` assembles `index.html` and `site/simulator.html`. |
| `backend/` | Python backend that pulls real wind, wave, current and temperature data and tests the simulator and capex assumptions. See `backend/README.md`. Data cache included, runs offline. |
| `models/` | Capex and cost-per-GPU-hour model, power-cost levers, sensitivity runs, pod thermal/availability sizing. |
| `docs/` | Pitch text and the latest assumption-test report. |

## Headline findings so far
- Real wind at 150 m is 12.6-14.1 m/s, not 10.5: the 2x overbuild + 12 h storage design serves 94-97% of load, and cost per sold GPU-hour falls from $5.66 to about $4.4-4.6 (terrestrial $2.61).
- Sea state is the blocker: a 72 h window under 2.5 m waves is open under 1% of hours, so the service campaign needs redesign.
- The simulator's hull heat-transfer curve is too steep (physics: 242 to 323 W/m2K, sim: 200 to 800), though the hull still rejects 0.96 MW at every site tested.

Assumptions marked [A] in the code are ours, not sourced. Currents are model output (HYCOM, four months of 2023).
