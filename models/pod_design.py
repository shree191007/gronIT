import math
from math import comb, log, pi

RACK_KW = 120.0
RACKS_PER_POD = 8
Q = RACKS_PER_POD * RACK_KW * 1e3          # W of heat per pod (~0.96 MW)
CP = 3.9e3                                  # J/kg/K, ~25% propylene glycol
RHO_W = 1025.0
CP_SEA = 4.0e3
D, L = 3.2, 12.0                            # pod envelope, m (assumed)
A_HULL = pi * D * L

def lmtd(Ts, Tr, Tsea):
    a, b = Tr - Tsea, Ts - Tsea
    return (a - b) / log(a / b)

print(f"Pod: {RACKS_PER_POD} racks, {Q/1e6:.2f} MW heat, bare hull area {A_HULL:.0f} m2 (D={D} m, L={L:.0f} m)")
dT = 10.0
mdot = Q / (CP * dT)
print(f"Coolant flow at 10 K rise: {mdot:.1f} kg/s = {mdot/1.02*60:.0f} L/min per pod ({mdot/1.02*60/RACKS_PER_POD:.0f} L/min per rack)")

print("\nTHERMAL: area needed for pod heat load (m2) and max heat for bare hull (MW); coolant rise 10 K")
print("Tsea  supply  LMTD   A_req@U200  @U400  @U800 | bare-hull Qmax@U200  @U400  @U800 | fin factor needed @U200/@U400")
for Tsea in (4, 8):
    for Ts in (22, 25, 30, 32):
        Tr = Ts + dT
        m = lmtd(Ts, Tr, Tsea)
        areq = [Q / (U * m) for U in (200, 400, 800)]
        qmax = [U * A_HULL * m / 1e6 for U in (200, 400, 800)]
        print(f"{Tsea:>3}C  {Ts:>3}C  {m:5.1f}K  {areq[0]:8.0f} {areq[1]:8.0f} {areq[2]:7.0f} | "
              f"{qmax[0]:8.2f} {qmax[1]:8.2f} {qmax[2]:8.2f}       | {areq[0]/A_HULL:4.1f}x / {areq[1]/A_HULL:4.1f}x")

print("\nBulk plume warming from one pod (flow past D x L cross-section)")
for v in (0.02, 0.05, 0.2, 0.5):
    dTb = Q / (RHO_W * CP_SEA * v * D * L)
    print(f"  current {v:4.2f} m/s -> {dTb:6.3f} K bulk;   whole 10-pod node in same stream: {dTb*10:6.3f} K")

print("\nPressure vs depth")
for z in (50, 100, 150, 200):
    p = 101325 + RHO_W * 9.81 * z
    print(f"  {z:>3} m: {p/1e6:5.2f} MPa absolute ({p/101325:4.1f} atm)")

# thermal ride-through
vol_L = 200 * RACKS_PER_POD + 400
mass = vol_L * 1.02
tth = mass * CP * 10 / Q
print(f"\nRide-through: ~{vol_L} L of coolant per pod -> {tth:.0f} s to +10 K at full load if pumps stop")

# rough pod mass
t_shell = 0.030
shell = pi * D * L * t_shell * 7850 / 1e3
mass_t = shell * 1.3 + RACKS_PER_POD * 1.8 + vol_L * 1.02 / 1e3 + 5
print(f"Rough pod mass: shell {shell:.0f} t (+30% heads/stiffeners) + racks {RACKS_PER_POD*1.8:.0f} t + coolant {vol_L*1.02/1e3:.1f} t + misc 5 t = ~{mass_t:.0f} t  [placeholder 30 mm shell]")

# ---------- availability ----------
print("\nAVAILABILITY: 10 duty pods (~9.6 MW) + s spare pods; pod-level common-cause event rate lam per pod-year")
print("restore time = mean wait for next service campaign (0.5 yr for annual campaign, 0.25 yr for twice-yearly)")
def p_full(N, need, q):
    return sum(comb(N, k) * (1 - q) ** k * q ** (N - k) for k in range(need, N + 1))
def e_cap(N, need, q):
    return sum(comb(N, k) * (1 - q) ** k * q ** (N - k) * min(k, need) for k in range(0, N + 1)) / need
print("lam   restore  spares  P(full capacity)  E[capacity]")
for lam in (0.02, 0.05, 0.10):
    for rest in (0.5, 0.25):
        q = lam * rest
        for s in (0, 1, 2):
            N = 10 + s
            print(f"{lam*100:4.0f}%  {rest:5.2f}yr   {s}      {p_full(N,10,q)*100:7.2f}%        {e_cap(N,10,q)*100:7.2f}%")

print("\nGPU attrition: yrs until 10% spare IT is exhausted (spare = 0.0909 of installed)")
print("annual permanent GPU loss p (x collateral m=2) x subsea factor f")
for p in (0.01, 0.03, 0.09):
    for f in (1.0, 0.5, 0.125):
        eff = p * 2 * f
        print(f"  p={p*100:3.0f}%/GPU-yr  f={f:5.3f}  -> {eff*100:5.2f}%/yr capacity loss -> {0.0909/eff:5.1f} yr")
print("\nLlama 3 anchor: (148+72) events x 365/54 / 16384 GPUs =",
      round((148+72)*365/54/16384*100, 1), "% interruptions per GPU-year (not all permanent)")
