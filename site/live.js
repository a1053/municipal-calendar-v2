/* Datos en vivo directo de ESPN desde el navegador (tabla y marcadores).
 * El sitio se reconstruye en GitHub, pero GitHub retrasa esas corridas horas; con esto la página
 * se pone al día sola cada vez que se abre o refresca. Funciones puras, probadas con Node;
 * si ESPN no responde o cambia el formato, el sitio sigue con los datos de la última corrida. */
(function (root) {
  "use strict";

  const STAT_KEYS = { gamesPlayed: "pj", wins: "g", ties: "e", losses: "p", pointsFor: "gf", pointsAgainst: "gc",
    pointDifferential: "dg", points: "pts", rank: "rank" };

  function num(v) {
    if (v && typeof v === "object") v = v.value !== undefined ? v.value : v.displayValue;
    if (v === null || v === undefined || v === "") return null;
    const f = Number(v);
    return Number.isFinite(f) ? f : null;
  }
  function logo(team) {
    if (team.logo) return team.logo;
    const l = team.logos && team.logos[0];
    return (l && l.href) || "";
  }

  /** Igual que standings_from_api de scripts/build_site_data.py. */
  function parseStandings(obj, teamId, teamName) {
    const groups = [];
    const nodes = (obj && obj.children && obj.children.length) ? obj.children : [obj || {}];
    nodes.forEach((child) => {
      const entries = (child.standings && child.standings.entries) || [];
      const rows = [];
      entries.forEach((e) => {
        const team = e.team || {};
        const row = { team_id: String(team.id === undefined ? "" : team.id),
          name: team.displayName || team.name || "", logo: logo(team) };
        const stats = {};
        (e.stats || []).forEach((s) => { if (s && typeof s === "object") stats[s.name] = num(s); });
        Object.keys(STAT_KEYS).forEach((k) => { row[STAT_KEYS[k]] = stats[k] === undefined ? null : stats[k]; });
        const note = e.note;
        row.note = note && typeof note === "object" ? (note.description || "") : "";
        if (row.name) rows.push(row);
      });
      if (!rows.length) return;
      rows.sort((a, b) => (a.rank === null ? 999 : a.rank) - (b.rank === null ? 999 : b.rank)
        || (b.pts || 0) - (a.pts || 0) || (b.dg || 0) - (a.dg || 0));
      rows.forEach((r, i) => {
        r.pos = i + 1;
        r.is_municipal = r.team_id === String(teamId) || r.name === teamName;
      });
      groups.push({ name: child.name || (child.standings && child.standings.name) || "", rows });
    });
    return groups;
  }

  const played = (groups) => ((groups && groups[0] && groups[0].rows) || []).reduce((a, r) => a + (r.pj || 0), 0);

  /** Solo se acepta una tabla completa y que no esté más atrasada que la publicada. */
  function chooseStandings(live, current) {
    const rows = (live && live[0] && live[0].rows) || [];
    if (rows.length < 8 || rows.some((r) => r.pj === null || r.pts === null)) return null;
    const have = current && current.groups ? played(current.groups) : 0;
    return played(live) >= have ? live : null;
  }

  /** Eventos de /scoreboard: { id: {state, completed, postponed, status, clock, date, home, away} }. */
  function parseScoreboard(obj) {
    const out = {};
    ((obj && obj.events) || []).forEach((ev) => {
      const comp = (ev.competitions || [])[0];
      if (!comp) return;
      const sides = {};
      (comp.competitors || []).forEach((c) => {
        sides[c.homeAway] = { id: String((c.team || {}).id === undefined ? "" : c.team.id), score: num(c.score) };
      });
      if (!sides.home || !sides.away) return;
      const status = comp.status || ev.status || {};
      const t = status.type || {};
      const state = t.state || "pre";
      const name = String(t.name || "").toUpperCase();
      out[String(ev.id)] = {
        state, completed: !!t.completed || state === "post",
        postponed: ["POSTPONED", "CANCELED", "CANCELLED", "SUSPENDED", "ABANDONED"].some((w) => name.includes(w)),
        status: t.shortDetail || t.detail || t.description || "", clock: status.displayClock || "",
        date: typeof ev.date === "string" ? ev.date : null, home: sides.home, away: sides.away,
      };
    });
    return out;
  }

  function resultFor(m, teamId, teamName) {
    if (m.state !== "post") return null;
    const h = m.home.score, a = m.away.score;
    if (h === null || h === undefined || a === null || a === undefined) return null;
    const mine = m.home.id === String(teamId) || m.home.name === teamName ? [h, a] : [a, h];
    return mine[0] > mine[1] ? "G" : mine[0] < mine[1] ? "P" : "E";
  }

  /** Copia de los partidos con estado, marcador y hora al día. Devuelve { matches, changed }. */
  function mergeMatches(matches, board, teamId, teamName) {
    let changed = 0;
    const out = matches.map((m) => {
      const b = board[m.id];
      if (!b) return m;
      const n = { ...m, home: { ...m.home }, away: { ...m.away } };
      n.state = b.state; n.completed = b.completed; n.postponed = b.postponed;
      n.status = b.status; n.clock = b.clock;
      if (b.home.score !== null) n.home.score = b.home.score;
      if (b.away.score !== null) n.away.score = b.away.score;
      if (b.date && !isNaN(Date.parse(b.date))) n.start = new Date(b.date).toISOString().replace(/\.\d{3}Z$/, "Z");
      n.result = resultFor(n, teamId, teamName);
      if (JSON.stringify([n.state, n.home.score, n.away.score, n.start, n.postponed, n.status])
        !== JSON.stringify([m.state, m.home.score, m.away.score, m.start, m.postponed, m.status])) changed++;
      return n;
    });
    return { matches: out, changed };
  }

  const ymd = (d) => d.toISOString().slice(0, 10).replace(/-/g, "");
  const scoreboardUrl = (slug, now) => `https://site.api.espn.com/apis/site/v2/sports/soccer/${slug}/scoreboard?dates=${ymd(new Date(now - 2 * 864e5))}-${ymd(new Date(+now + 14 * 864e5))}&limit=100`;
  const standingsUrl = (slug) => `https://site.api.espn.com/apis/v2/sports/soccer/${slug}/standings`;

  const api = { parseStandings, chooseStandings, parseScoreboard, mergeMatches, resultFor, scoreboardUrl, standingsUrl };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniLive = api;
})(typeof window !== "undefined" ? window : globalThis);
