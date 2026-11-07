/* Textos para compartir por WhatsApp (resultado, tabla, liguilla). Funciones puras, probadas con Node:
 * tests/share.test.js. Las fechas ya vienen formateadas desde la página. */
(function (root) {
  "use strict";

  const MAX = 1500; // el enlace de WhatsApp se corta si es demasiado largo
  const trim = (t) => (t.length > MAX ? `${t.slice(0, MAX - 1)}…` : t);
  const pctText = (n) => (n == null ? "" : n > 99 && n < 100 ? ">99%" : n > 0 && n < 1 ? "<1%" : `${Math.round(n)}%`);

  /** Mensaje de un partido según su estado: ya jugado, en vivo o por jugar. */
  function matchText(m, o) {
    const home = m.home.name, away = m.away.name, comp = o.competition ? ` (${o.competition})` : "";
    let head;
    if (m.state === "post" && m.home.score != null) head = `Final${comp}: ${home} ${m.home.score}-${m.away.score} ${away}`;
    else if (m.state === "in") head = `EN VIVO${comp}: ${home} ${m.home.score ?? 0}-${m.away.score ?? 0} ${away}${m.status ? ` (${m.status})` : ""}`;
    else if (m.postponed) head = `Partido aplazado${comp}: ${home} vs ${away}`;
    else head = `Próximo partido${comp}: ${home} vs ${away}${o.when ? `, ${o.when}` : ""}`;
    const tv = m.state !== "post" && m.broadcasts && m.broadcasts.length ? `\nDónde verlo: ${m.broadcasts.join(", ")}` : "";
    return trim(`${head}${tv}\n${o.url}`);
  }

  /** Mensaje con la tabla: los primeros lugares y la posición de Municipal. */
  function tableText(rows, o) {
    const q = o.qualify || 6;
    const top = rows.slice(0, Math.max(q, 6)).map((r, i) => `${i + 1}. ${r.name} ${r.pts} pts`).join("\n");
    const me = rows.find((r) => r.is_municipal);
    const mine = me && me.pos > Math.max(q, 6) ? `\n...\n${me.pos}. ${me.name} ${me.pts} pts` : "";
    return trim(`Tabla de la Liga Bantrab${o.tournament ? ` (${o.tournament})` : ""}:\n${top}${mine}\n${o.url}`);
  }

  /** Mensaje de la liguilla: dónde va Municipal y sus probabilidades, si existen. */
  function ligaText(summary, odds, o) {
    const lines = [`Liguilla${o.tournament ? ` del ${o.tournament}` : ""}: si terminara hoy`, ...(summary || []).slice(0, 3)];
    if (odds) lines.push(`Probabilidad de clasificar: ${pctText(odds.p_qualify)}. De pasar directo a semifinales: ${pctText(odds.p_direct)}.`);
    lines.push(o.url);
    return trim(lines.join("\n"));
  }

  const whatsappUrl = (text) => `https://wa.me/?text=${encodeURIComponent(text)}`;

  const api = { matchText, tableText, ligaText, whatsappUrl };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniShare = api;
})(typeof window !== "undefined" ? window : globalThis);
