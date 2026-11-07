/* Liguilla del Apertura: llave "si terminara hoy" y situación de cada equipo.
 * Funciones puras (sin DOM) probadas con Node: tests/liguilla.test.js
 *
 * Reglas (Apertura 2026, según Emisoras Unidas y Claro Sports):
 *  - Clasifican 6. El 1.º y el 2.º van directo a semifinales.
 *  - Ronda previa: 3.º contra 6.º y 4.º contra 5.º.
 *  - Semifinales: el 1.º juega contra el peor ubicado de los dos ganadores
 *    de la ronda previa y el 2.º contra el mejor ubicado.
 *  - En cada serie el mejor clasificado juega la vuelta en casa (dato de Jorge).
 *  - La fase regular termina cuando todos juegan 22 partidos.
 * Las posiciones vienen de ESPN tal cual (su orden ya incluye los desempates).
 */
(function (root) {
  "use strict";

  const DEFAULTS = { rounds: 22, qualify: 6, direct: 2 };
  const opt = (o) => ({ ...DEFAULTS, ...(o || {}) });
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const ord = (n) => `${n}.º`;

  /** Partidos que le faltan a cada equipo y el máximo de puntos que aún puede sumar. */
  function situation(rows, o) {
    const { rounds, qualify, direct } = opt(o);
    const list = rows.map((r) => {
      const left = r.pj == null ? null : Math.max(0, rounds - r.pj);
      return { ...r, left, max: left == null || r.pts == null ? null : r.pts + 3 * left };
    });
    return list.map((t) => {
      if (t.max == null) return { ...t, status: "unknown" };
      const others = list.filter((x) => x !== t && x.max != null);
      // Con empate de puntos no se sabe quién queda arriba, así que se cuenta como "puede quedar arriba".
      const canReach = others.filter((x) => x.max >= t.pts).length;
      const surelyAbove = others.filter((x) => x.pts > t.max).length;
      let status = "alive";
      if (canReach <= direct - 1) status = "direct";
      else if (canReach <= qualify - 1) status = "qualified";
      else if (surelyAbove >= qualify) status = "out";
      else if (surelyAbove >= direct) status = "no-direct";
      return { ...t, status };
    });
  }

  function progress(rows, o) {
    const { rounds } = opt(o);
    const pjs = rows.map((r) => r.pj).filter((n) => n != null);
    if (!pjs.length) return null;
    const left = pjs.reduce((a, n) => a + Math.max(0, rounds - n), 0);
    return { rounds, minPJ: Math.min(...pjs), maxPJ: Math.max(...pjs), matchesLeft: Math.ceil(left / 2), done: left === 0 };
  }

  const seedOf = (r, i) => ({ seed: i + 1, id: r.team_id, name: r.name, logo: r.logo, pts: r.pts, is_municipal: !!r.is_municipal });

  function tie(id, round, a, b, labels) {
    // a y b: equipos o null. "hi" es el de mejor posición: cierra de local.
    let hi = a, lo = b;
    if (a && b && b.seed < a.seed) { hi = b; lo = a; }
    return { id, round, hi, lo, labels: labels || [], winner: null };
  }

  /**
   * Arma la llave con los clasificados y las elecciones del usuario.
   * picks: { P1: seed, P2: seed, S1: seed, S2: seed, F: seed }  (número de posición del ganador)
   * Devuelve { seeds, rounds: [{name, ties}], champion, picks } o null si faltan equipos.
   */
  function bracket(rows, picks, o) {
    const { qualify, direct } = opt(o);
    if (!rows || rows.length < qualify) return null;
    const seeds = rows.slice(0, qualify).map(seedOf);
    const clean = {};
    const pick = (t) => {
      const want = picks && picks[t.id];
      if (t.hi && t.lo && (want === t.hi.seed || want === t.lo.seed)) {
        clean[t.id] = want;
        t.winner = want === t.hi.seed ? t.hi : t.lo;
      }
      return t.winner;
    };

    // Ronda previa: 3.º-6.º y 4.º-5.º (en general: el que sigue a los directos contra el último, etc.)
    const prelim = [];
    for (let k = 0; k < (qualify - direct) / 2; k++) {
      prelim.push(tie(`P${k + 1}`, "Ronda previa", seeds[direct + k], seeds[qualify - 1 - k]));
    }
    const winners = prelim.map(pick);

    // Semifinales: el 1.º contra el peor ubicado de los ganadores; el 2.º contra el mejor ubicado.
    const known = winners.every(Boolean) ? winners.slice().sort((x, y) => x.seed - y.seed) : null;
    const s1 = tie("S1", "Semifinales", seeds[0], known ? known[known.length - 1] : null, ["Peor ubicado de los ganadores"]);
    const s2 = tie("S2", "Semifinales", seeds[1], known ? known[0] : null, ["Mejor ubicado de los ganadores"]);
    if (!known) { s1.hi = seeds[0]; s2.hi = seeds[1]; }
    const finalists = [pick(s1), pick(s2)];

    const f = tie("F", "Final", finalists[0], finalists[1], ["Ganador de la semifinal 1", "Ganador de la semifinal 2"]);
    if (!(finalists[0] && finalists[1])) { f.hi = null; f.lo = null; }
    const champion = pick(f);

    return { seeds, rounds: [{ name: "Ronda previa", ties: prelim }, { name: "Semifinales", ties: [s1, s2] }, { name: "Final", ties: [f] }], champion, picks: clean };
  }

  /** Frases sobre cómo está un equipo respecto a la liguilla si la fase regular terminara hoy. */
  function summary(rows, teamId, o) {
    const { qualify, direct } = opt(o);
    const list = situation(rows, o);
    const idx = list.findIndex((r) => String(r.team_id) === String(teamId) || r.is_municipal);
    if (idx < 0) return [];
    const t = list[idx], pos = idx + 1, out = [];
    const nameOf = (i) => (list[i] ? list[i].name : "");
    out.push(`${t.name} es ${ord(pos)} con ${plural(t.pts, "punto", "puntos")}.`);
    if (pos <= direct) {
      out.push(`Si la fase regular terminara hoy, pasaría directo a semifinales.`);
    } else if (pos <= qualify) {
      const oppPos = direct + qualify + 1 - pos;
      const home = pos < oppPos ? "cerraría de local" : "cerraría de visitante";
      out.push(`Si la fase regular terminara hoy, jugaría la ronda previa contra el ${ord(oppPos)} (${nameOf(oppPos - 1)}) y ${home} la serie.`);
    } else {
      out.push(`Si la fase regular terminara hoy, quedaría fuera de la liguilla.`);
    }
    if (pos > direct && list[direct - 1]) {
      const gap = list[direct - 1].pts - t.pts;
      out.push(gap === 0 ? `Está igualado en puntos con el ${ord(direct)} (${nameOf(direct - 1)}).`
        : `Está a ${plural(gap, "punto", "puntos")} del ${ord(direct)} (${nameOf(direct - 1)}).`);
    }
    if (pos <= qualify && list[qualify]) {
      const gap = t.pts - list[qualify].pts;
      out.push(`Le lleva ${plural(gap, "punto", "puntos")} al ${ord(qualify + 1)} (${nameOf(qualify)}).`);
    } else if (pos > qualify && list[qualify - 1]) {
      const gap = list[qualify - 1].pts - t.pts;
      out.push(gap === 0 ? `Está igualado en puntos con el ${ord(qualify)} (${nameOf(qualify - 1)}).`
        : `Está a ${plural(gap, "punto", "puntos")} del ${ord(qualify)} (${nameOf(qualify - 1)}).`);
    }
    if (t.left != null) out.push(`Le ${t.left === 1 ? "falta" : "faltan"} ${plural(t.left, "partido", "partidos")} y puede sumar hasta ${t.max} puntos.`);
    return out;
  }

  const api = { DEFAULTS, situation, progress, bracket, summary };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniLiguilla = api;
})(typeof window !== "undefined" ? window : globalThis);
