/* 2D lattice-Boltzmann flow (D2Q9, BGK) around a circular pod cross-section,
   with a passive temperature field (semi-Lagrangian) and Boussinesq buoyancy. */
function createSim(o) {
  const nx = o.nx, ny = o.ny, N = nx * ny;
  const R = o.R, pcx = o.cx, pcy = o.cy;
  const tau = o.tau;
  const cx = [0, 1, 0, -1, 0, 1, -1, -1, 1];
  const cy = [0, 0, 1, 0, -1, 1, 1, -1, -1];
  const w = [4 / 9, 1 / 9, 1 / 9, 1 / 9, 1 / 9, 1 / 36, 1 / 36, 1 / 36, 1 / 36];
  const opp = [0, 3, 4, 1, 2, 7, 8, 5, 6];

  let f = new Float32Array(9 * N);
  let g = new Float32Array(9 * N);
  const ux = new Float32Array(N), uy = new Float32Array(N);
  let T = new Float32Array(N), T2 = new Float32Array(N);
  const solid = new Uint8Array(N);
  let U = 0.04;
  let buoy = 0;          // lattice acceleration per kelvin
  let kappa = 0.012;     // scalar diffusion, cells^2 per step
  const eqIn = new Float32Array(9);

  function feq(i, rho, vx, vy) {
    const cu = cx[i] * vx + cy[i] * vy;
    return w[i] * rho * (1 + 3 * cu + 4.5 * cu * cu - 1.5 * (vx * vx + vy * vy));
  }
  function setU(u) {
    U = u;
    for (let i = 0; i < 9; i++) eqIn[i] = feq(i, 1, U, 0);
  }
  setU(U);

  for (let y = 0; y < ny; y++) for (let x = 0; x < nx; x++) {
    const dx = x - pcx, dy = y - pcy;
    if (dx * dx + dy * dy <= R * R) solid[y * nx + x] = 1;
  }
  // hull-adjacent fluid cells and a sampling ring around the pod
  const hull = [];
  const ring = [];
  for (let y = 1; y < ny - 1; y++) for (let x = 1; x < nx - 1; x++) {
    const idx = y * nx + x;
    if (solid[idx]) continue;
    if (solid[idx - 1] || solid[idx + 1] || solid[idx - nx] || solid[idx + nx]) hull.push(idx);
    const d = Math.hypot(x - pcx, y - pcy);
    if (d >= R + 2 && d <= R + 6) ring.push(idx);
  }
  const hullIdx = Int32Array.from(hull);
  const ringIdx = Int32Array.from(ring);

  // paint an approximate downstream plume so the first frame is not empty
  function seedPlume(amp) {
    for (let y = 0; y < ny; y++) for (let x = pcx; x < nx; x++) {
      const idx = y * nx + x;
      if (solid[idx]) continue;
      const s = R * 0.55 + 0.06 * (x - pcx);
      const dy = y - pcy;
      T[idx] = amp * Math.exp(-(dy * dy) / (2 * s * s)) * Math.exp(-(x - pcx) / 120);
    }
  }

  function init() {
    for (let idx = 0; idx < N; idx++) {
      const x = idx % nx, y = (idx / nx) | 0;
      const pert = (solid[idx] ? 0 : 1) * 0.002 * Math.sin(0.35 * x) * Math.exp(-((y - pcy) * (y - pcy)) / 400);
      for (let i = 0; i < 9; i++) f[i * N + idx] = feq(i, 1, U, pert);
      ux[idx] = U; uy[idx] = 0; T[idx] = 0;
    }
  }
  init();

  function collide() {
    const inv = 1 / tau;
    for (let idx = 0; idx < N; idx++) {
      if (solid[idx]) continue;
      let rho = 0, mx = 0, my = 0;
      for (let i = 0; i < 9; i++) {
        const fi = f[i * N + idx];
        rho += fi; mx += cx[i] * fi; my += cy[i] * fi;
      }
      const vx = mx / rho, vy0 = my / rho;
      let ay = buoy * T[idx];
      if (ay > 0.002) ay = 0.002;
      const vy = vy0 + tau * ay;
      ux[idx] = vx; uy[idx] = vy0 + 0.5 * ay;
      const u2 = vx * vx + vy * vy;
      for (let i = 0; i < 9; i++) {
        const cu = cx[i] * vx + cy[i] * vy;
        const e = w[i] * rho * (1 + 3 * cu + 4.5 * cu * cu - 1.5 * u2);
        const k = i * N + idx;
        f[k] += (e - f[k]) * inv;
      }
    }
  }

  function stream() {
    for (let idx = 0; idx < N; idx++) {
      if (solid[idx]) continue;
      const x = idx % nx, y = (idx / nx) | 0;
      for (let i = 0; i < 9; i++) {
        const sx = x - cx[i], sy = y - cy[i];
        let val;
        if (sx < 0 || sy < 0 || sy >= ny) val = eqIn[i];
        else if (sx >= nx) val = f[i * N + idx];
        else {
          const s = sy * nx + sx;
          val = solid[s] ? f[opp[i] * N + idx] : f[i * N + s];
        }
        g[i * N + idx] = val;
      }
    }
    const t = f; f = g; g = t;
  }

  function advectScalar() {
    for (let idx = 0; idx < N; idx++) {
      if (solid[idx]) { T2[idx] = 0; continue; }
      const x = idx % nx, y = (idx / nx) | 0;
      let px = x - ux[idx], py = y - uy[idx];
      if (px < 0) px = 0; else if (px > nx - 1.001) px = nx - 1.001;
      if (py < 0) py = 0; else if (py > ny - 1.001) py = ny - 1.001;
      const x0 = px | 0, y0 = py | 0, fx = px - x0, fy = py - y0;
      const i00 = y0 * nx + x0, i10 = i00 + 1, i01 = i00 + nx, i11 = i01 + 1;
      let w00 = (1 - fx) * (1 - fy), w10 = fx * (1 - fy), w01 = (1 - fx) * fy, w11 = fx * fy;
      if (solid[i00]) w00 = 0; if (solid[i10]) w10 = 0; if (solid[i01]) w01 = 0; if (solid[i11]) w11 = 0;
      const sw = w00 + w10 + w01 + w11;
      T2[idx] = sw > 1e-6 ? (w00 * T[i00] + w10 * T[i10] + w01 * T[i01] + w11 * T[i11]) / sw : T[idx];
    }
    // diffusion (explicit, Neumann at solids and edges)
    for (let y = 0; y < ny; y++) for (let x = 0; x < nx; x++) {
      const idx = y * nx + x;
      if (solid[idx]) { T[idx] = 0; continue; }
      const c = T2[idx];
      const l = x > 0 && !solid[idx - 1] ? T2[idx - 1] : c;
      const r = x < nx - 1 && !solid[idx + 1] ? T2[idx + 1] : c;
      const d = y > 0 && !solid[idx - nx] ? T2[idx - nx] : c;
      const u = y < ny - 1 && !solid[idx + nx] ? T2[idx + nx] : c;
      T[idx] = c + kappa * (l + r + d + u - 4 * c);
    }
    for (let y = 0; y < ny; y++) T[y * nx] = 0;   // inflow is ambient
  }

  function deposit(dT) {
    for (let k = 0; k < hullIdx.length; k++) T[hullIdx[k]] += dT;
  }

  function step(n, dTdep) {
    for (let s = 0; s < n; s++) {
      collide();
      stream();
      advectScalar();
      if (dTdep > 0) deposit(dTdep);
    }
  }

  function ringMean() {
    let s = 0;
    for (let k = 0; k < ringIdx.length; k++) s += T[ringIdx[k]];
    return ringIdx.length ? s / ringIdx.length : 0;
  }
  function maxT() {
    let m = 0;
    for (let i = 0; i < N; i++) if (T[i] > m) m = T[i];
    return m;
  }
  function sane() {
    for (let i = 0; i < N; i += 7) {
      if (!isFinite(ux[i]) || !isFinite(uy[i]) || !isFinite(T[i])) return false;
    }
    return true;
  }

  return {
    nx, ny, N, R, cx: pcx, cy: pcy, solid, ux, uy,
    get T() { return T; },
    hullCount: hullIdx.length,
    setU, setBuoy(b) { buoy = b; }, setKappa(k) { kappa = k; },
    step, ringMean, maxT, sane, init, seedPlume,
  };
}
if (typeof module !== 'undefined') module.exports = { createSim };
