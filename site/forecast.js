/* Pronóstico de un partido de liga: mismo modelo que scripts/odds.py.
 * Goles esperados = promedio de la liga x ataque propio x defensa rival, con ventaja de local;
 * los goles siguen una distribución Poisson. Funciones puras, probadas con Node. */
(function (root) {
  "use strict";
  const PRIOR_GAMES = 6, HOME_BOOST = 1.18, MAX_GOALS = 10;

  function strengths(rows) {
    let pj = 0, gf = 0;
    rows.forEach((r) => { pj += r.pj || 0; gf += r.gf || 0; });
    const mu = pj && gf ? gf / pj : 1.1;
    const out = {};
    rows.forEach((r) => {
      const n = r.pj || 0;
      out[r.team_id] = {
        att: ((r.gf || 0) + PRIOR_GAMES * mu) / (n + PRIOR_GAMES) / mu,
        def: ((r.gc || 0) + PRIOR_GAMES * mu) / (n + PRIOR_GAMES) / mu,
      };
    });
    return { mu, st: out };
  }

  function poisson(lam) {
    const p = [Math.exp(-lam)];
    for (let k = 1; k <= MAX_GOALS; k++) p.push(p[k - 1] * lam / k);
    return p;
  }

  /** null si algún equipo no está en la tabla o faltan datos. */
  function forecast(rows, homeId, awayId) {
    if (!rows || !rows.length) return null;
    const h = rows.find((r) => String(r.team_id) === String(homeId));
    const a = rows.find((r) => String(r.team_id) === String(awayId));
    if (!h || !a || h === a || [h, a].some((r) => r.pj == null || r.gf == null || r.gc == null)) return null;
    const { mu, st } = strengths(rows.filter((r) => r.pj != null));
    const xgH = mu * HOME_BOOST * st[h.team_id].att * st[a.team_id].def;
    const xgA = mu / HOME_BOOST * st[a.team_id].att * st[h.team_id].def;
    const ph = poisson(xgH), pa = poisson(xgA);
    let win = 0, draw = 0, loss = 0;
    const scores = [];
    for (let i = 0; i <= MAX_GOALS; i++) {
      for (let j = 0; j <= MAX_GOALS; j++) {
        const p = ph[i] * pa[j];
        if (i > j) win += p; else if (i === j) draw += p; else loss += p;
        scores.push({ home: i, away: j, p });
      }
    }
    const total = win + draw + loss;
    scores.sort((x, y) => y.p - x.p);
    return {
      xgHome: xgH, xgAway: xgA,
      pHome: win / total * 100, pDraw: draw / total * 100, pAway: loss / total * 100,
      topScores: scores.slice(0, 3).map((s) => ({ home: s.home, away: s.away, p: s.p / total * 100 })),
    };
  }

  const api = { forecast, strengths };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniForecast = api;
})(typeof window !== "undefined" ? window : globalThis);
