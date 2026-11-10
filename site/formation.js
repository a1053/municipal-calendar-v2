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
    return ta[0][0] === tb[0][0] && ta[ta.length - 1] === tb[tb.length - 1];
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

  const api = { estimate, same };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniFormation = api;
})(typeof window !== "undefined" ? window : globalThis);
