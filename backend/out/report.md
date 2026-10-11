# Neocloud assumption tests

Generated 2026-10-11T06:51:51Z. Verdicts: OK = data supports the assumption, WATCH = marginal, FAIL = data contradicts it in the unfavourable direction, OFF (better) = data differs in our favour.

| Check | Drake Passage | Kerguelen Plateau, south | SE Pacific ACC | Offshore southern Chile |
|---|---|---|---|---|
| C1 Sea temperature at pod depth | WATCH, better | WATCH, better | OK | OK |
| C2 Current speed at pod depth | OK | FAIL | WATCH, better | FAIL |
| C3 Seawater volumetric heat capacity | OK | OK | OK | OK |
| C4 Hull heat-transfer coefficient U | FAIL | WATCH | FAIL | WATCH |
| C5 Can the hull reject 0.96 MW? | OK | OK | OK | OK |
| C6 Bulk warming of the water passing a pod | WATCH | FAIL | WATCH | FAIL |
| C7 Hub-height wind resource | OFF, better than assumed | OFF, better than assumed | OFF, better than assumed | OFF, better than assumed |
| C8 Wind gaps: share of load served at 2x overbuild + 12 h storage | OFF, better than assumed | OFF, better than assumed | OFF, better than assumed | OFF, better than assumed |
| C9 Sea state for pod swaps (72 h windows) | FAIL | FAIL | FAIL | FAIL |
| C10 Cost per GPU-hour with real wind | OFF, better than assumed | OFF, better than assumed | OFF, better than assumed | OFF, better than assumed |

## Drake Passage (-58.5, -63.0)

**C1 Sea temperature at pod depth: WATCH, better**  
Assumed: 4.0 C at 150 m, slider range 0.0-10.0 C  
Observed median 1.2 C, colder than the 4.0 C default; 85% of profiles fall inside the slider range. Colder sea helps heat rejection, so a warm default is the conservative side.  
Change: Set the default sea temperature to about 1.2 C for this site; keep the 0-10 C range.

**C2 Current speed at pod depth: OK**  
Assumed: 0.2 m/s typical, slider 0.01-0.5 m/s  
Median 0.16 m/s (P5 0.05, P95 0.51); 5.0% of 3-hourly samples are below 0.05 m/s; direction steadiness 0.57 (1 = one-way flow).  
Change: Add this site's P5/P50/P95 as presets on the current slider; model slack water as a first-class case.

**C3 Seawater volumetric heat capacity: OK**  
Assumed: rho*cp = 4.1 MJ/m3/K; nu = 1.56e-6 m2/s in the Reynolds readout  
TEOS-10 gives rho*cp = 4.099 MJ/m3/K at 1.2 C (0.0% from the sim). Kinematic viscosity is 1.78e-6 m2/s, so the Reynolds readout is 12% high.  
Change: Change the Reynolds readout to use nu = 1.62e-6 m2/s at 4 C (minor).

**C4 Hull heat-transfer coefficient U: FAIL**  
Assumed: U = 200 + 1200 v  W/m2K (200 still, 800 at 0.5 m/s)  
Still-water U matches (242 vs 200) because turbulent natural convection is strong at a 25 K wall-sea difference, but the sim's slope is too steep: at 0.5 m/s physics gives 323 against 800, since the glycol side, steel wall and fouling cap U at about 612 W/m2K and the outside film is no longer the only resistance. Worst sim/physics ratio across P10-P90 currents is 2.2x.  
Change: Replace the sim's U with a curve fitted to the physics: roughly 242 W/m2K still rising to 323 at 0.5 m/s. Inner-side h and fouling are my [A] values and the slope is sensitive to them.

**C5 Can the hull reject 0.96 MW?: OK**  
Assumed: Hull area x1.5 (U = 200 + 1200 v) rejects the full pod load at a normal 22 to 32 C loop  
To reject 0.96 MW with the x1.5 hull (fins at 85% efficiency) at this site's weakest-current case (P5, 0.05 m/s), the coolant supply must be 20.0 C; at the median current 19.2 C. The sim's own U would say 17.0 C. Full-power operation without throttling needs a supply of 27 C or less (chip model Tj = coolant + 38 K, throttle at 70 C); the vendor maximum is 32 C.  
Change: If the needed supply is above 27 C, add area (target bare-hull factor of about 1.3 before fin efficiency) or plan on throttling during weak-current periods.

**C6 Bulk warming of the water passing a pod: WATCH**  
Assumed: 0.03 K for one pod at 0.2 m/s; 10 pods in the same stream add linearly  
Ten in-line pods warm the passing water by 0.39 K at the median current and 1.22 K at P95; it exceeds the 0.5 K illustrative limit 33.1% of the time. Values below 0.02 m/s are floored there, where the real plume turns buoyant and rises instead of diluting.  
Change: Stagger pods across the stream (cross-flow spacing) so no pod sits in another's wake, and agree a real ecological limit with the ecology team.

**C7 Hub-height wind resource: OFF, better than assumed**  
Assumed: mean 10.5 m/s (range 9.0-12.0), Weibull k = 2.2  
MERRA-2 gives a mean of 12.6 m/s at 150 m (shear exponent 0.115 fitted from 10 m and 50 m, extrapolated), 2.1 m/s above the 10.5 m/s base case. Weibull k fits at 2.82 (sim 2.2). Capacity factor per turbine 72% with the capex model's power curve and 10% losses. Cross-check: ERA5 100 m is +2.0% against MERRA-2 over 8 common years (hourly correlation 0.95).  
Change: Use 12.6 m/s as this site's base wind. Reanalyses smooth gusts and wakes, and the 50 m to 150 m extrapolation adds uncertainty, so treat it as slightly optimistic.

**C8 Wind gaps: share of load served at 2x overbuild + 12 h storage: OFF, better than assumed**  
Assumed: Synthetic Weibull + AR(1, rho 0.985) wind, served fraction from the capex model  
With real hourly wind the 2x/12 h design serves 94.4% of the load, against 84.0% for the synthetic series at the same mean (10.4 points more). Years vary from 91.5% to 97.0%. Longest stretch below 5 m/s is 57 h in reality versus 174 h synthetic. The capex base case (synthetic, 10.5 m/s mean) serves 77.9%. A 90% served fraction needs only 1.4x overbuild with 12 h storage here.  
Change: Replace the synthetic wind in capex_model.py with this site's ERA5 series; use the served_grid to re-pick overbuild and storage.

**C9 Sea state for pod swaps (72 h windows): FAIL**  
Assumed: An annual service/recovery campaign is possible (capex model: $8M/yr)  
Median significant wave height is 3.5 m and the 99th percentile 7.6 m (max 12.4 m). A 72 h window with Hs under 2.5 m is open 0.5% of hours over the year and 1.6% in the best three months (month 6).  
Change: Budget weather standby days in the campaign cost, size the work for Hs 3 m or more with a DP vessel, or shorten the swap procedure below 72 h.

**C10 Cost per GPU-hour with real wind: OFF, better than assumed**  
Assumed: Base case: $5.66 per sold GPU-hour (synthetic wind, 2x overbuild, 12 h storage), terrestrial $2.61  
With this site's real wind the base design costs $4.71 per sold GPU-hour (-17% against the capex base case $5.66) because it serves 94% instead of 79%. Re-optimised (1.5x overbuild, 12 h storage) it reaches $4.59, -19% against base and +76% against terrestrial ($2.61). Everything else in the capex model is unchanged.  
Change: Feed each site's wind series into capex_model.py and re-pick overbuild and storage; wind capex and storage are the levers that move.


## Kerguelen Plateau, south (-55.0, 75.0)

**C1 Sea temperature at pod depth: WATCH, better**  
Assumed: 4.0 C at 150 m, slider range 0.0-10.0 C  
Observed median 1.0 C, colder than the 4.0 C default; 90% of profiles fall inside the slider range. Colder sea helps heat rejection, so a warm default is the conservative side.  
Change: Set the default sea temperature to about 1.0 C for this site; keep the 0-10 C range.

**C2 Current speed at pod depth: FAIL**  
Assumed: 0.2 m/s typical, slider 0.01-0.5 m/s  
Median 0.05 m/s (P5 0.01, P95 0.14); 54.4% of 3-hourly samples are below 0.05 m/s; direction steadiness 0.37 (1 = one-way flow).  
Change: Add this site's P5/P50/P95 as presets on the current slider; model slack water as a first-class case.

**C3 Seawater volumetric heat capacity: OK**  
Assumed: rho*cp = 4.1 MJ/m3/K; nu = 1.56e-6 m2/s in the Reynolds readout  
TEOS-10 gives rho*cp = 4.099 MJ/m3/K at 1.0 C (0.0% from the sim). Kinematic viscosity is 1.79e-6 m2/s, so the Reynolds readout is 13% high.  
Change: Change the Reynolds readout to use nu = 1.62e-6 m2/s at 4 C (minor).

**C4 Hull heat-transfer coefficient U: WATCH**  
Assumed: U = 200 + 1200 v  W/m2K (200 still, 800 at 0.5 m/s)  
Still-water U matches (241 vs 200) because turbulent natural convection is strong at a 25 K wall-sea difference, but the sim's slope is too steep: at 0.5 m/s physics gives 323 against 800, since the glycol side, steel wall and fouling cap U at about 612 W/m2K and the outside film is no longer the only resistance. Worst sim/physics ratio across P10-P90 currents is 1.3x.  
Change: Replace the sim's U with a curve fitted to the physics: roughly 241 W/m2K still rising to 323 at 0.5 m/s. Inner-side h and fouling are my [A] values and the slope is sensitive to them.

**C5 Can the hull reject 0.96 MW?: OK**  
Assumed: Hull area x1.5 (U = 200 + 1200 v) rejects the full pod load at a normal 22 to 32 C loop  
To reject 0.96 MW with the x1.5 hull (fins at 85% efficiency) at this site's weakest-current case (P5, 0.01 m/s), the coolant supply must be 20.0 C; at the median current 19.9 C. The sim's own U would say 21.3 C. Full-power operation without throttling needs a supply of 27 C or less (chip model Tj = coolant + 38 K, throttle at 70 C); the vendor maximum is 32 C.  
Change: If the needed supply is above 27 C, add area (target bare-hull factor of about 1.3 before fin efficiency) or plan on throttling during weak-current periods.

**C6 Bulk warming of the water passing a pod: FAIL**  
Assumed: 0.03 K for one pod at 0.2 m/s; 10 pods in the same stream add linearly  
Ten in-line pods warm the passing water by 1.33 K at the median current and 3.05 K at P95; it exceeds the 0.5 K illustrative limit 93.2% of the time. Values below 0.02 m/s are floored there, where the real plume turns buoyant and rises instead of diluting.  
Change: Stagger pods across the stream (cross-flow spacing) so no pod sits in another's wake, and agree a real ecological limit with the ecology team.

**C7 Hub-height wind resource: OFF, better than assumed**  
Assumed: mean 10.5 m/s (range 9.0-12.0), Weibull k = 2.2  
MERRA-2 gives a mean of 14.1 m/s at 150 m (shear exponent 0.090 fitted from 10 m and 50 m, extrapolated), 3.6 m/s above the 10.5 m/s base case. Weibull k fits at 2.96 (sim 2.2). Capacity factor per turbine 76% with the capex model's power curve and 10% losses. Cross-check: ERA5 100 m is +3.4% against MERRA-2 over 4 common years (hourly correlation 0.96).  
Change: Use 14.1 m/s as this site's base wind. Reanalyses smooth gusts and wakes, and the 50 m to 150 m extrapolation adds uncertainty, so treat it as slightly optimistic.

**C8 Wind gaps: share of load served at 2x overbuild + 12 h storage: OFF, better than assumed**  
Assumed: Synthetic Weibull + AR(1, rho 0.985) wind, served fraction from the capex model  
With real hourly wind the 2x/12 h design serves 96.9% of the load, against 85.4% for the synthetic series at the same mean (11.6 points more). Years vary from 94.1% to 98.1%. Longest stretch below 5 m/s is 44 h in reality versus 134 h synthetic. The capex base case (synthetic, 10.5 m/s mean) serves 77.9%. A 90% served fraction needs only 1.3x overbuild with 12 h storage here.  
Change: Replace the synthetic wind in capex_model.py with this site's ERA5 series; use the served_grid to re-pick overbuild and storage.

**C9 Sea state for pod swaps (72 h windows): FAIL**  
Assumed: An annual service/recovery campaign is possible (capex model: $8M/yr)  
Median significant wave height is 4.2 m and the 99th percentile 8.4 m (max 11.8 m). A 72 h window with Hs under 2.5 m is open 0.2% of hours over the year and 0.7% in the best three months (month 12).  
Change: Budget weather standby days in the campaign cost, size the work for Hs 3 m or more with a DP vessel, or shorten the swap procedure below 72 h.

**C10 Cost per GPU-hour with real wind: OFF, better than assumed**  
Assumed: Base case: $5.66 per sold GPU-hour (synthetic wind, 2x overbuild, 12 h storage), terrestrial $2.61  
With this site's real wind the base design costs $4.59 per sold GPU-hour (-19% against the capex base case $5.66) because it serves 97% instead of 79%. Re-optimised (1.25x overbuild, 4 h storage) it reaches $4.40, -22% against base and +68% against terrestrial ($2.61). Everything else in the capex model is unchanged.  
Change: Feed each site's wind series into capex_model.py and re-pick overbuild and storage; wind capex and storage are the levers that move.


## SE Pacific ACC (-57.0, -120.0)

**C1 Sea temperature at pod depth: OK**  
Assumed: 4.0 C at 150 m, slider range 0.0-10.0 C  
Observed median 4.4 C, warmer than the 4.0 C default; 100% of profiles fall inside the slider range. Colder sea helps heat rejection, so a warm default is the conservative side.  
Change: Set the default sea temperature to about 4.4 C for this site; keep the 0-10 C range.

**C2 Current speed at pod depth: WATCH, better**  
Assumed: 0.2 m/s typical, slider 0.01-0.5 m/s  
Median 0.31 m/s (P5 0.05, P95 0.61); 4.8% of 3-hourly samples are below 0.05 m/s; direction steadiness 0.49 (1 = one-way flow).  
Change: Add this site's P5/P50/P95 as presets on the current slider; model slack water as a first-class case.

**C3 Seawater volumetric heat capacity: OK**  
Assumed: rho*cp = 4.1 MJ/m3/K; nu = 1.56e-6 m2/s in the Reynolds readout  
TEOS-10 gives rho*cp = 4.098 MJ/m3/K at 4.4 C (0.0% from the sim). Kinematic viscosity is 1.60e-6 m2/s, so the Reynolds readout is 3% high.  
Change: Change the Reynolds readout to use nu = 1.62e-6 m2/s at 4 C (minor).

**C4 Hull heat-transfer coefficient U: FAIL**  
Assumed: U = 200 + 1200 v  W/m2K (200 still, 800 at 0.5 m/s)  
Still-water U matches (244 vs 200) because turbulent natural convection is strong at a 25 K wall-sea difference, but the sim's slope is too steep: at 0.5 m/s physics gives 329 against 800, since the glycol side, steel wall and fouling cap U at about 612 W/m2K and the outside film is no longer the only resistance. Worst sim/physics ratio across P10-P90 currents is 2.5x.  
Change: Replace the sim's U with a curve fitted to the physics: roughly 244 W/m2K still rising to 329 at 0.5 m/s. Inner-side h and fouling are my [A] values and the slope is sensitive to them.

**C5 Can the hull reject 0.96 MW?: OK**  
Assumed: Hull area x1.5 (U = 200 + 1200 v) rejects the full pod load at a normal 22 to 32 C loop  
To reject 0.96 MW with the x1.5 hull (fins at 85% efficiency) at this site's weakest-current case (P5, 0.052 m/s), the coolant supply must be 22.4 C; at the median current 19.6 C. The sim's own U would say 20.0 C. Full-power operation without throttling needs a supply of 27 C or less (chip model Tj = coolant + 38 K, throttle at 70 C); the vendor maximum is 32 C.  
Change: If the needed supply is above 27 C, add area (target bare-hull factor of about 1.5 before fin efficiency) or plan on throttling during weak-current periods.

**C6 Bulk warming of the water passing a pod: WATCH**  
Assumed: 0.03 K for one pod at 0.2 m/s; 10 pods in the same stream add linearly  
Ten in-line pods warm the passing water by 0.20 K at the median current and 1.18 K at P95; it exceeds the 0.5 K illustrative limit 12.3% of the time. Values below 0.02 m/s are floored there, where the real plume turns buoyant and rises instead of diluting.  
Change: Stagger pods across the stream (cross-flow spacing) so no pod sits in another's wake, and agree a real ecological limit with the ecology team.

**C7 Hub-height wind resource: OFF, better than assumed**  
Assumed: mean 10.5 m/s (range 9.0-12.0), Weibull k = 2.2  
MERRA-2 gives a mean of 13.7 m/s at 150 m (shear exponent 0.090 fitted from 10 m and 50 m, extrapolated), 3.2 m/s above the 10.5 m/s base case. Weibull k fits at 2.92 (sim 2.2). Capacity factor per turbine 75% with the capex model's power curve and 10% losses. Cross-check: ERA5 100 m is +2.2% against MERRA-2 over 7 common years (hourly correlation 0.96).  
Change: Use 13.7 m/s as this site's base wind. Reanalyses smooth gusts and wakes, and the 50 m to 150 m extrapolation adds uncertainty, so treat it as slightly optimistic.

**C8 Wind gaps: share of load served at 2x overbuild + 12 h storage: OFF, better than assumed**  
Assumed: Synthetic Weibull + AR(1, rho 0.985) wind, served fraction from the capex model  
With real hourly wind the 2x/12 h design serves 96.3% of the load, against 85.2% for the synthetic series at the same mean (11.1 points more). Years vary from 94.7% to 98.3%. Longest stretch below 5 m/s is 66 h in reality versus 134 h synthetic. The capex base case (synthetic, 10.5 m/s mean) serves 77.9%. A 90% served fraction needs only 1.3x overbuild with 12 h storage here.  
Change: Replace the synthetic wind in capex_model.py with this site's ERA5 series; use the served_grid to re-pick overbuild and storage.

**C9 Sea state for pod swaps (72 h windows): FAIL**  
Assumed: An annual service/recovery campaign is possible (capex model: $8M/yr)  
Median significant wave height is 3.9 m and the 99th percentile 8.7 m (max 12.5 m). A 72 h window with Hs under 2.5 m is open 0.9% of hours over the year and 1.7% in the best three months (month 3).  
Change: Budget weather standby days in the campaign cost, size the work for Hs 3 m or more with a DP vessel, or shorten the swap procedure below 72 h.

**C10 Cost per GPU-hour with real wind: OFF, better than assumed**  
Assumed: Base case: $5.66 per sold GPU-hour (synthetic wind, 2x overbuild, 12 h storage), terrestrial $2.61  
With this site's real wind the base design costs $4.62 per sold GPU-hour (-18% against the capex base case $5.66) because it serves 96% instead of 79%. Re-optimised (1.25x overbuild, 4 h storage) it reaches $4.44, -21% against base and +70% against terrestrial ($2.61). Everything else in the capex model is unchanged.  
Change: Feed each site's wind series into capex_model.py and re-pick overbuild and storage; wind capex and storage are the levers that move.


## Offshore southern Chile (-53.5, -76.5)

**C1 Sea temperature at pod depth: OK**  
Assumed: 4.0 C at 150 m, slider range 0.0-10.0 C  
Observed median 5.6 C, warmer than the 4.0 C default; 100% of profiles fall inside the slider range. Colder sea helps heat rejection, so a warm default is the conservative side.  
Change: Set the default sea temperature to about 5.6 C for this site; keep the 0-10 C range.

**C2 Current speed at pod depth: FAIL**  
Assumed: 0.2 m/s typical, slider 0.01-0.5 m/s  
Median 0.07 m/s (P5 0.02, P95 0.12); 33.2% of 3-hourly samples are below 0.05 m/s; direction steadiness 0.38 (1 = one-way flow).  
Change: Add this site's P5/P50/P95 as presets on the current slider; model slack water as a first-class case.

**C3 Seawater volumetric heat capacity: OK**  
Assumed: rho*cp = 4.1 MJ/m3/K; nu = 1.56e-6 m2/s in the Reynolds readout  
TEOS-10 gives rho*cp = 4.098 MJ/m3/K at 5.6 C (0.0% from the sim). Kinematic viscosity is 1.54e-6 m2/s, so the Reynolds readout is 1% high.  
Change: Change the Reynolds readout to use nu = 1.62e-6 m2/s at 4 C (minor).

**C4 Hull heat-transfer coefficient U: WATCH**  
Assumed: U = 200 + 1200 v  W/m2K (200 still, 800 at 0.5 m/s)  
Still-water U matches (245 vs 200) because turbulent natural convection is strong at a 25 K wall-sea difference, but the sim's slope is too steep: at 0.5 m/s physics gives 331 against 800, since the glycol side, steel wall and fouling cap U at about 612 W/m2K and the outside film is no longer the only resistance. Worst sim/physics ratio across P10-P90 currents is 1.3x.  
Change: Replace the sim's U with a curve fitted to the physics: roughly 245 W/m2K still rising to 331 at 0.5 m/s. Inner-side h and fouling are my [A] values and the slope is sensitive to them.

**C5 Can the hull reject 0.96 MW?: OK**  
Assumed: Hull area x1.5 (U = 200 + 1200 v) rejects the full pod load at a normal 22 to 32 C loop  
To reject 0.96 MW with the x1.5 hull (fins at 85% efficiency) at this site's weakest-current case (P5, 0.017 m/s), the coolant supply must be 23.4 C; at the median current 23.3 C. The sim's own U would say 24.9 C. Full-power operation without throttling needs a supply of 27 C or less (chip model Tj = coolant + 38 K, throttle at 70 C); the vendor maximum is 32 C.  
Change: If the needed supply is above 27 C, add area (target bare-hull factor of about 1.5 before fin efficiency) or plan on throttling during weak-current periods.

**C6 Bulk warming of the water passing a pod: FAIL**  
Assumed: 0.03 K for one pod at 0.2 m/s; 10 pods in the same stream add linearly  
Ten in-line pods warm the passing water by 0.94 K at the median current and 3.05 K at P95; it exceeds the 0.5 K illustrative limit 95.5% of the time. Values below 0.02 m/s are floored there, where the real plume turns buoyant and rises instead of diluting.  
Change: Stagger pods across the stream (cross-flow spacing) so no pod sits in another's wake, and agree a real ecological limit with the ecology team.

**C7 Hub-height wind resource: OFF, better than assumed**  
Assumed: mean 10.5 m/s (range 9.0-12.0), Weibull k = 2.2  
MERRA-2 gives a mean of 13.7 m/s at 150 m (shear exponent 0.089 fitted from 10 m and 50 m, extrapolated), 3.2 m/s above the 10.5 m/s base case. Weibull k fits at 2.87 (sim 2.2). Capacity factor per turbine 74% with the capex model's power curve and 10% losses. Cross-check: ERA5 100 m is +1.6% against MERRA-2 over 4 common years (hourly correlation 0.96).  
Change: Use 13.7 m/s as this site's base wind. Reanalyses smooth gusts and wakes, and the 50 m to 150 m extrapolation adds uncertainty, so treat it as slightly optimistic.

**C8 Wind gaps: share of load served at 2x overbuild + 12 h storage: OFF, better than assumed**  
Assumed: Synthetic Weibull + AR(1, rho 0.985) wind, served fraction from the capex model  
With real hourly wind the 2x/12 h design serves 94.4% of the load, against 85.2% for the synthetic series at the same mean (9.2 points more). Years vary from 91.1% to 96.3%. Longest stretch below 5 m/s is 107 h in reality versus 134 h synthetic. The capex base case (synthetic, 10.5 m/s mean) serves 77.9%. A 90% served fraction needs only 1.3x overbuild with 12 h storage here.  
Change: Replace the synthetic wind in capex_model.py with this site's ERA5 series; use the served_grid to re-pick overbuild and storage.

**C9 Sea state for pod swaps (72 h windows): FAIL**  
Assumed: An annual service/recovery campaign is possible (capex model: $8M/yr)  
Median significant wave height is 4.2 m and the 99th percentile 8.1 m (max 10.7 m). A 72 h window with Hs under 2.5 m is open 0.6% of hours over the year and 1.4% in the best three months (month 7).  
Change: Budget weather standby days in the campaign cost, size the work for Hs 3 m or more with a DP vessel, or shorten the swap procedure below 72 h.

**C10 Cost per GPU-hour with real wind: OFF, better than assumed**  
Assumed: Base case: $5.66 per sold GPU-hour (synthetic wind, 2x overbuild, 12 h storage), terrestrial $2.61  
With this site's real wind the base design costs $4.71 per sold GPU-hour (-17% against the capex base case $5.66) because it serves 94% instead of 79%. Re-optimised (1.25x overbuild, 4 h storage) it reaches $4.52, -20% against base and +73% against terrestrial ($2.61). Everything else in the capex model is unchanged.  
Change: Feed each site's wind series into capex_model.py and re-pick overbuild and storage; wind capex and storage are the levers that move.

## Limits of this test

- Currents are HYCOM model output (not measurements) for four months of 2023 only; treat site rankings as indicative and validate with moorings or glider data before design freeze.
- Wind is reanalysis (MERRA-2 10 m and 50 m, extrapolated to 150 m; ERA5 agrees within about 3%). Reanalyses smooth gusts, and storm shutdowns, icing and platform-motion downtime are not modelled.
- Wave data begin in April 2021 (about 3.5 years), so extremes are under-sampled.
- Hull U uses assumed inner-side h (1,500 W/m2K) and fouling (3e-4 m2K/W); natural-convection h is good to roughly +-30%. Fins are credited at 85% efficiency.
- Design limits for plume warming (0.5 K) and service sea state (Hs 2.5 m, 72 h) are our own placeholders and drive those verdicts.
- Not testable with open data: GPU rack price and power, satellite link capacity and cost, floating-wind capex, EM and ecological thresholds.

## Data sources

Argo float profiles, Ifremer ERDDAP ArgoFloats (erddap.ifremer.fr), QC flag 1
Churchill-Bernstein / Churchill-Chu correlations; Sharqawy et al. 2010 seawater properties; TEOS-10 (gsw)
ECMWF ERA5 via Open-Meteo archive API (archive-api.open-meteo.com)
HYCOM GLBy0.08 expt 93.0 analysis, THREDDS NCSS (tds.hycom.org); a model, not observations
NASA POWER hourly WS10M and WS50M, MERRA-2 reanalysis (power.larc.nasa.gov)
Open-Meteo marine archive, wave model reanalysis from April 2021 (marine-api.open-meteo.com)