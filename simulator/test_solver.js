const { createSim } = require('./solver.js');

function run(label, tau, U, buoyPerK, qDep, steps) {
  const sim = createSim({ nx: 256, ny: 112, R: 13, cx: 52, cy: 56, tau });
  sim.setU(U); sim.setBuoy(buoyPerK);
  const t0 = process.hrtime.bigint();
  let minUy = 1, maxUy = -1;
  for (let s = 0; s < steps; s++) {
    sim.step(1, qDep);
    if (s > steps * 0.6) {
      const p = (56 + 4) * 256 + 52 + 26;   // probe in the wake
      const v = sim.uy[p];
      if (v < minUy) minUy = v; if (v > maxUy) maxUy = v;
    }
  }
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  let maxU = 0;
  for (let i = 0; i < sim.N; i++) { const m = Math.hypot(sim.ux[i], sim.uy[i]); if (m > maxU) maxU = m; }
  console.log(`${label.padEnd(34)} tau=${tau} U=${U} steps=${steps} ${(ms / steps).toFixed(2)} ms/step ` +
    `sane=${sim.sane()} maxSpeed=${maxU.toFixed(3)} wakeUy[${minUy.toFixed(4)},${maxUy.toFixed(4)}] ` +
    `Tmax=${sim.maxT().toFixed(3)} ring=${sim.ringMean().toFixed(4)} hullCells=${sim.hullCount}`);
  return sim;
}

for (const tau of [0.515, 0.52, 0.53]) {
  run('mid current', tau, 0.04, 0, 6e-4, 2500);
}
run('high current', 0.52, 0.082, 0, 6e-4, 2500);
run('high current tau .515', 0.515, 0.082, 0, 6e-4, 2500);
run('low current + buoyancy', 0.52, 0.0134, 6.6e-5, 6.3e-4 * 4, 2500);
run('low current strong heat', 0.52, 0.0134, 6.6e-5, 6.3e-4 * 12, 3000);
run('mid current, heavy heat', 0.52, 0.04, 0, 6e-4 * 8, 2500);
