/* Alineación dibujada en cancha: reparte a los titulares en filas según la formación ("4-3-3").
 * Función pura probada con Node (tests/pitch.test.js). Devuelve null si no se puede dibujar,
 * y la página muestra entonces solo la lista. */
(function (root) {
  "use strict";

  /** Filas de abajo (portero) hacia arriba (delanteros): [[portero], [defensas...], ..., [delanteros...]]. */
  function layout(formation, players) {
    const starters = (players || []).filter((p) => p.starter);
    const nums = String(formation || "").split("-").map((n) => parseInt(n, 10));
    if (starters.length !== 11 || nums.length < 2 || nums.some((n) => !(n > 0)) || nums.reduce((a, b) => a + b, 0) !== 10) return null;
    const placed = starters.every((p) => p.place > 0);
    const ordered = placed ? starters.slice().sort((a, b) => a.place - b.place) : starters.slice();
    const gk = ordered.findIndex((p) => /^(G|GK|POR)/i.test(p.pos || ""));
    if (gk > 0) ordered.unshift(ordered.splice(gk, 1)[0]); // el portero siempre primero
    const rows = [[ordered[0]]];
    let i = 1;
    nums.forEach((n) => { rows.push(ordered.slice(i, i + n)); i += n; });
    return rows;
  }

  /** Apellido corto para el nombre bajo el círculo. */
  function shortName(name) {
    const parts = String(name || "").trim().split(/\s+/);
    if (parts.length <= 1) return parts[0] || "";
    const small = /^(de|del|la|las|los|da|do|dos|van|von|di|le)$/i;
    let last = parts[parts.length - 1], k = parts.length - 2;
    while (k > 0 && small.test(parts[k])) { last = `${parts[k]} ${last}`; k--; }
    return last;
  }

  const api = { layout, shortName };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniPitch = api;
})(typeof window !== "undefined" ? window : globalThis);
