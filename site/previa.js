/* Previa de un partido: comparación de los dos equipos con los datos de la tabla.
 * Funciones puras (sin DOM), probadas con Node: tests/previa.test.js
 * Solo usa lo que ya hay: tabla de la liga, últimos partidos y goleadores. Si falta algo, no inventa nada. */
(function (root) {
  "use strict";

  const per = (n, pj) => (pj ? Math.round((n / pj) * 10) / 10 : null);   // 1 decimal: se compara lo mismo que se muestra
  const fix = (n) => (n == null ? "-" : n.toFixed(1));
  const sign = (n) => (n > 0 ? `+${n}` : String(n));

  function stats(row) {
    if (!row || !row.pj) return null;
    return { name: row.name, pos: row.pos == null ? null : row.pos, pts: row.pts, pj: row.pj, ppg: per(row.pts, row.pj),
      gfpg: per(row.gf, row.pj), gcpg: per(row.gc, row.pj), dg: row.dg };
  }

  /** Filas de la comparación. better: "a", "b" o null (empate o dato que falta). */
  function compare(rows, aId, bId) {
    const find = (id) => (rows || []).find((r) => String(r.team_id) === String(id));
    const a = stats(find(aId)), b = stats(find(bId));
    if (!a || !b || String(aId) === String(bId)) return null;
    const row = (label, va, vb, fmt, lowerIsBetter) => {
      let better = null;
      if (va != null && vb != null && va !== vb) better = (va < vb) === !!lowerIsBetter ? "a" : "b";
      return { label, a: fmt(va), b: fmt(vb), better };
    };
    const rowsOut = [
      row("Posición", a.pos, b.pos, (v) => (v == null ? "-" : `${v}.º`), true),
      row("Puntos", a.pts, b.pts, (v) => (v == null ? "-" : String(v)), false),
      row("Puntos por partido", a.ppg, b.ppg, fix, false),
      row("Goles a favor por partido", a.gfpg, b.gfpg, fix, false),
      row("Goles en contra por partido", a.gcpg, b.gcpg, fix, true),
      row("Diferencia de goles", a.dg, b.dg, (v) => (v == null ? "-" : sign(v)), false),
    ];
    return { a, b, rows: rowsOut };
  }

  /** Dos frases: cómo llega cada uno y quién tiene el mejor ataque y la mejor defensa. */
  function headline(cmp) {
    if (!cmp) return [];
    const { a, b } = cmp;
    const out = [];
    if (a.pos != null && b.pos != null) {
      out.push(`${a.name} llega ${a.pos}.º con ${a.pts} puntos; ${b.name} llega ${b.pos}.º con ${b.pts}.`);
    }
    const atk = a.gfpg != null && b.gfpg != null && a.gfpg !== b.gfpg ? (a.gfpg > b.gfpg ? [a, b] : [b, a]) : null;
    const def = a.gcpg != null && b.gcpg != null && a.gcpg !== b.gcpg ? (a.gcpg < b.gcpg ? [a, b] : [b, a]) : null;
    const A = atk && `marca más (${fix(atk[0].gfpg)} goles por partido contra ${fix(atk[1].gfpg)})`;
    const D = def && `recibe menos (${fix(def[0].gcpg)} contra ${fix(def[1].gcpg)})`;
    if (atk && def && atk[0] === def[0]) out.push(`${atk[0].name} ${A} y ${D}.`);
    else if (atk && def) out.push(`${atk[0].name} ${A}; ${def[0].name} ${D}.`);
    else if (atk) out.push(`${atk[0].name} ${A}.`);
    else if (def) out.push(`${def[0].name} ${D}.`);
    return out;
  }

  /** Los que más goles llevan (solo con goles). players: [{name, goals}] */
  function topScorers(players, n) {
    return (players || []).filter((p) => p && p.goals > 0)
      .slice().sort((x, y) => y.goals - x.goals || String(x.name).localeCompare(String(y.name))).slice(0, n || 3)
      .map((p) => ({ name: p.name, goals: p.goals }));
  }

  /** Últimos partidos de un equipo a partir del calendario: [{result, vs, home, score}] (los más viejos primero). */
  function recentForm(matches, teamId, n) {
    const mine = (matches || []).filter((m) => m.state === "post" && !m.postponed && m.result
      && (String(m.home.id) === String(teamId) || String(m.away.id) === String(teamId)))
      .sort((x, y) => String(y.start).localeCompare(String(x.start))).slice(0, n || 5);
    return mine.map((m) => {
      const home = String(m.home.id) === String(teamId), opp = home ? m.away : m.home;
      return { result: m.result, vs: opp.name, home, score: `${m.home.score}-${m.away.score}`, start: m.start };
    }).reverse();
  }

  const api = { compare, headline, topScorers, recentForm };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniPrevia = api;
})(typeof window !== "undefined" ? window : globalThis);
