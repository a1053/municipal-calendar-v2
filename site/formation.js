/* Formación estimada: cuando una alineación no trae formación ni posiciones (OneFootball), se cruzan los
 * titulares con el plantel de ESPN (posición de cada jugador) y se cuentan defensas, medios y delanteros.
 * Es una estimación: la página la marca así. Función pura probada con Node (tests/formation.test.js). */
(function (root) {
  "use strict";

  const norm = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().match(/[a-z]+/g) || [];

  /** ¿Mismo jugador escrito distinto? Mismo nombre completo, o misma inicial y mismo apellido, o primer nombre y algún otro token. */
  function same(a, b) {
    const ta = norm(a), tb = norm(b);
    if (ta.length < 2 || tb.length < 2) return false;
    if (ta.join(" ") === tb.join(" ")) return true;
    const shared = ta.filter((t) => t.length > 2 && tb.includes(t));
    if (ta[0] === tb[0] && shared.length >= 2) return true;
    if (ta[0][0] === tb[0][0] && ta[ta.length - 1] === tb[tb.length - 1]) return true;
    // error de tipeo en un nombre ("Aubrey Devid" / "Aubrey David"): mismo primer nombre y apellido a una letra de distancia
    const la = ta[ta.length - 1], lb = tb[tb.length - 1];
    return ta[0] === tb[0] && la.length >= 4 && lb.length >= 4 && edits(la, lb) <= 1;
  }

  /** Distancia de edición entre dos palabras cortas. */
  function edits(a, b) {
    const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
    for (let j = 1; j <= b.length; j++) d[0][j] = j;
    for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    return d[a.length][b.length];
  }

  const LETTER = ["G", "D", "M", "F"];

  /** Devuelve {formation, players} con `pos` y `place` asignados, o null si no se puede estimar con seguridad. */
  function estimate(players, roster) {
    const starters = (players || []).filter((p) => p.starter);
    if (starters.length !== 11 || !(roster || []).length) return null;
    const used = new Set();
    const tagged = starters.map((p) => {
      const idx = roster.findIndex((r, i) => !used.has(i) && LETTER[r.pos_order] && same(p.name, r.name));
      if (idx < 0) return null;
      used.add(idx);
      return { ...p, pos: LETTER[roster[idx].pos_order], _g: roster[idx].pos_order };
    });
    if (tagged.some((p) => !p)) return null;               // faltó un titular: mejor no dibujar algo falso
    const count = [0, 0, 0, 0];
    tagged.forEach((p) => count[p._g]++);
    if (count[0] !== 1 || count[1] < 3 || count[2] < 2 || count[3] < 1) return null;
    const sorted = tagged.slice().sort((a, b) => a._g - b._g || (Number(a.jersey) || 99) - (Number(b.jersey) || 99));
    sorted.forEach((p, i) => { p.place = i + 1; delete p._g; });
    return { formation: `${count[1]}-${count[2]}-${count[3]}`, players: [...sorted, ...(players || []).filter((p) => !p.starter)] };
  }

  /** Marcas de cada jugador (goles, tarjetas, cambios) sacadas de los eventos del partido. Alineaciones a mano ya las traen. */
  function withMarks(lineup, events) {
    if (!lineup || !(events || []).length) return lineup;
    const evs = events.filter((e) => !e.team_id || !lineup.team_id || String(e.team_id) === String(lineup.team_id));
    const surname = (n) => norm(n).slice(-1)[0] || "";
    const bySurname = {};
    lineup.players.forEach((p) => { const k = surname(p.name); bySurname[k] = (bySurname[k] || 0) + 1; });
    // Mismo jugador: nombre parecido, o el mismo apellido cuando es único en la alineación ("E Ávalos" / "Víctor Avalos").
    const is = (p, name) => {
      if (!name) return false;
      if (norm(p.name).join(" ") === norm(name).join(" ") || same(p.name, name)) return true;
      const k = surname(name);
      return k.length > 3 && k === surname(p.name) && bySurname[k] === 1;
    };
    const EVENT_MARKS = ["goal", "yellow", "red", "in", "out"];
    // ESPN y OneFootball son la fuente oficial: las marcas de eventos salen solo de ahí. De lo manual queda el capitán.
    const players = lineup.players.map((p) => {
      const marks = (p.marks || []).filter((k) => !EVENT_MARKS.includes(k));
      evs.forEach((e) => {
        if (e.kind === "goal" && is(p, e.player)) marks.push("goal");
        else if (e.kind === "yellow" && is(p, e.player)) marks.push("yellow");
        else if (e.kind === "red" && is(p, e.player)) marks.push("red");
        else if (e.kind === "sub") {
          if (is(p, e.player)) marks.push("in");
          if (is(p, e.player_out)) marks.push("out");
        }
      });
      return marks.length || p.marks ? { ...p, marks } : p;
    });
    return { ...lineup, players };
  }

  const api = { estimate, same, withMarks };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniFormation = api;
})(typeof window !== "undefined" ? window : globalThis);
