/* Estadísticas de Municipal calculadas con los partidos de matches.json.
 * Funciones puras (sin DOM) para poder probarlas con Node: tests/stats.test.js */
(function (root) {
  "use strict";

  const isMe = (side, teamId, teamName) => String(side.id) === String(teamId) || side.name === teamName;

  /** Partidos ya jugados y con marcador, vistos desde Municipal, del más viejo al más nuevo. */
  function played(matches, teamId, teamName) {
    return (matches || [])
      .filter((m) => m.state === "post" && !m.postponed && m.home.score != null && m.away.score != null)
      .map((m) => {
        const home = isMe(m.home, teamId, teamName);
        const me = home ? m.home : m.away, other = home ? m.away : m.home;
        const gf = Number(me.score), gc = Number(other.score);
        return { id: m.id, start: m.start, competition: m.competition, home, vs: other.name, gf, gc,
                 res: gf > gc ? "G" : gf < gc ? "P" : "E" };
      })
      .sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0));
  }

  const bucket = () => ({ pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0 });

  function streak(list, ok) {
    let n = 0;
    for (let i = list.length - 1; i >= 0 && ok(list[i].res); i--) n++;
    return n;
  }

  function summarize(list) {
    const total = bucket(), home = bucket(), away = bucket();
    let cleanSheets = 0, failedToScore = 0;
    for (const x of list) {
      for (const b of [total, x.home ? home : away]) {
        b.pj++; b[x.res.toLowerCase()]++; b.gf += x.gf; b.gc += x.gc;
      }
      if (x.gc === 0) cleanSheets++;
      if (x.gf === 0) failedToScore++;
    }
    const pts = 3 * total.g + total.e;
    const per = (n) => (total.pj ? n / total.pj : null);
    return {
      ...total, pts, ppg: per(pts), winPct: total.pj ? (100 * total.g) / total.pj : null,
      dg: total.gf - total.gc, gfpg: per(total.gf), gcpg: per(total.gc),
      cleanSheets, failedToScore, home, away,
      streak: { win: streak(list, (r) => r === "G"), unbeaten: streak(list, (r) => r !== "P"), loss: streak(list, (r) => r === "P") },
      last: list.slice(-5),
    };
  }

  /** Próximos partidos (hasta n), con indicador de local/visitante. */
  function nextMatches(matches, nowMs, teamId, teamName, n) {
    return (matches || [])
      .filter((m) => m.state === "pre" && !m.postponed && Date.parse(m.start) > nowMs - 3 * 3600e3)
      .sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0))
      .slice(0, n == null ? 5 : n)
      .map((m) => {
        const home = isMe(m.home, teamId, teamName);
        return { id: m.id, start: m.start, competition: m.competition, home, vs: (home ? m.away : m.home).name };
      });
  }

  const pl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const ord = (n) => `${n}.º`;

  /**
   * Frases en español a partir de las cifras.
   * o = { team, scope: {all: bool, label}, stats, standing: {pos, pts, pj, league} | null,
   *       next: [...], fmt: { day(iso), time(iso) } }
   */
  function narrative(o) {
    const out = [], s = o.stats, T = o.team;
    if (o.standing && o.standing.pos != null && o.standing.pts != null) {
      out.push(`${T} es ${ord(o.standing.pos)} de la ${o.standing.league} con ${pl(o.standing.pts, "punto", "puntos")}` +
        (o.standing.pj != null ? ` en ${pl(o.standing.pj, "partido", "partidos")}.` : "."));
    }
    if (s.pj === 0) {
      out.push(`Todavía no ha jugado partidos${o.scope.all ? "" : ` en ${o.scope.label}`}.`);
    } else {
      out.push(`${o.scope.all ? "En total" : `En ${o.scope.label}`} ha jugado ${pl(s.pj, "partido", "partidos")}: ` +
        `${pl(s.g, "ganado", "ganados")}, ${pl(s.e, "empatado", "empatados")} y ${pl(s.p, "perdido", "perdidos")}, ` +
        `con ${pl(s.gf, "gol", "goles")} a favor y ${s.gc} en contra.`);
      const last = s.last;
      if (last.length >= 2) {
        const c = (r) => last.filter((x) => x.res === r).length;
        out.push(`En sus últimos ${last.length} partidos ganó ${c("G")}, empató ${c("E")} y perdió ${c("P")}.`);
      }
      if (s.streak.win >= 3) out.push(`Ganó sus últimos ${s.streak.win} partidos.`);
      else if (s.streak.unbeaten >= 3) out.push(`Lleva ${s.streak.unbeaten} partidos sin perder.`);
      else if (s.streak.loss >= 2) out.push(`Perdió sus últimos ${s.streak.loss} partidos.`);
      if (s.pj >= 3 && s.cleanSheets > 0) {
        out.push(`Dejó su portería en cero en ${s.cleanSheets} de ${s.pj} partidos.`);
      }
    }
    const nx = o.next || [];
    if (nx.length) {
      const first = nx[0], where = first.home ? "de local" : "de visitante";
      const when = `el ${o.fmt.day(first.start)} a las ${o.fmt.time(first.start)}`;
      const dot = (t) => (t.endsWith(".") ? t : `${t}.`); // "p. m." ya trae su punto
      if (nx.length === 1) {
        out.push(dot(`Su próximo partido es ${where} contra ${first.vs}, ${when}`));
      } else {
        const h = nx.filter((x) => x.home).length, a = nx.length - h;
        out.push(`De sus próximos ${nx.length} partidos, ${h} ${h === 1 ? "es" : "son"} de local y ` +
          `${a} ${a === 1 ? "es" : "son"} de visitante. ` + dot(`El siguiente es ${where} contra ${first.vs}, ${when}`));
      }
    }
    return out;
  }

  const api = { played, summarize, nextMatches, narrative, ordinal: ord, plural: pl };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniStats = api;
})(typeof window !== "undefined" ? window : globalThis);
