/* Imagen vertical (1080x1920) para historias de WhatsApp/Instagram. `cardModel` es pura (tests/sharecard.test.js);
 * `drawCard` dibuja en un canvas y `makeBlob` devuelve el PNG. Si un escudo no carga, se dibujan las iniciales. */
(function (root) {
  "use strict";

  const W = 1080, H = 1920;
  const MAX_SCORERS = 6;

  /** Datos ya listos para dibujar. `o.when` y `o.competition` llegan formateados desde la página. */
  function cardModel(m, events, o) {
    const state = m.postponed ? "postponed" : m.state === "post" && m.home.score != null ? "post" : m.state === "in" ? "in" : "pre";
    const scored = state === "post" || state === "in";
    const side = (s) => ({ name: s.name, logo: s.logo || null, score: scored ? (s.score == null ? 0 : s.score) : null });
    const scorers = scored ? (events || []).filter((e) => (e.kind === "goal" || e.kind === "own_goal") && e.player)
      .slice(0, MAX_SCORERS).map((e) => ({
        home: e.team_id === m.home.id, min: e.min || "",
        text: `${e.player}${e.kind === "own_goal" ? " (autogol)" : e.penalty ? " (p)" : ""}` })) : [];
    const headline = { post: "Final", in: m.status ? `En vivo ${m.status}` : "En vivo", pre: "Próximo partido", postponed: "Aplazado" }[state];
    return { state, headline, competition: o.competition || "", when: state === "pre" || state === "postponed" ? (o.when || "") : "",
      home: side(m.home), away: side(m.away), scorers, tv: state === "pre" && m.broadcasts && m.broadcasts.length ? m.broadcasts.join(", ") : "",
      footer: o.footer || "" };
  }

  const initials = (n) => n.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

  function loadImage(src) {
    return new Promise((res) => {
      if (!src) return res(null);
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => res(img);
      img.onerror = () => res(null);
      img.src = src;
    });
  }

  function fit(ctx, text, max, font) {          // achica la letra hasta que el texto cabe
    let size = parseInt(font, 10);
    for (; size > 24; size -= 4) { ctx.font = font.replace(/\d+px/, `${size}px`); if (ctx.measureText(text).width <= max) break; }
    return size;
  }

  function crest(ctx, img, name, cx, cy, r) {
    ctx.save();
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill(); ctx.clip();
    if (img) { const s = Math.min((2 * r - 24) / img.width, (2 * r - 24) / img.height); ctx.drawImage(img, cx - img.width * s / 2, cy - img.height * s / 2, img.width * s, img.height * s); }
    else { ctx.fillStyle = "#2b0a0f"; ctx.font = `800 ${r * 0.8}px sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(initials(name), cx, cy + 4); }
    ctx.restore();
  }

  async function drawCard(canvas, model) {
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext("2d");
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, "#d01c24"); g.addColorStop(0.45, "#2b0a0f"); g.addColorStop(1, "#150b0d");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.textAlign = "center"; ctx.textBaseline = "alphabetic"; ctx.fillStyle = "#fff";
    ctx.font = "700 44px sans-serif"; ctx.globalAlpha = 0.85; ctx.fillText(model.competition, W / 2, 150); ctx.globalAlpha = 1;
    ctx.fillStyle = "#ffb400"; ctx.font = "800 120px 'Big Shoulders Display','Arial Narrow',Impact,sans-serif";
    ctx.fillText(model.headline.toUpperCase(), W / 2, 300);
    const [hi, ai] = await Promise.all([loadImage(model.home.logo), loadImage(model.away.logo)]);
    crest(ctx, hi, model.home.name, 290, 600, 170); crest(ctx, ai, model.away.name, 790, 600, 170);
    ctx.fillStyle = "#fff";
    [[model.home, 290], [model.away, 790]].forEach(([s, x]) => { const f = `700 52px sans-serif`; fit(ctx, s.name, 440, f); ctx.fillText(s.name, x, 860); });
    ctx.font = "800 300px 'Big Shoulders Display','Arial Narrow',Impact,sans-serif";
    if (model.home.score != null) { ctx.fillText(`${model.home.score}  -  ${model.away.score}`, W / 2, 1180); }
    else { ctx.font = "800 200px 'Big Shoulders Display','Arial Narrow',Impact,sans-serif"; ctx.fillText("VS", W / 2, 1130); }
    let y = 1290;
    if (model.when) { ctx.font = "700 60px sans-serif"; ctx.fillText(model.when, W / 2, y); y += 90; }
    if (model.tv) { ctx.font = "500 44px sans-serif"; ctx.globalAlpha = 0.85; ctx.fillText(`Dónde verlo: ${model.tv}`, W / 2, y); ctx.globalAlpha = 1; }
    if (model.scorers.length) {
      ctx.font = "600 46px sans-serif";
      model.scorers.forEach((s) => {
        ctx.textAlign = s.home ? "right" : "left";
        ctx.fillText(`${s.text} ${s.min}`, s.home ? W / 2 - 40 : W / 2 + 40, y); y += 70;
      });
      ctx.textAlign = "center";
    }
    ctx.font = "600 38px sans-serif"; ctx.globalAlpha = 0.7; ctx.fillText(model.footer, W / 2, H - 110); ctx.globalAlpha = 1;
  }

  /** PNG del canvas, o null si el navegador lo bloquea (escudos de otro dominio sin permiso). */
  function toBlob(canvas) {
    return new Promise((res) => { try { canvas.toBlob((b) => res(b), "image/png"); } catch (_) { res(null); } });
  }

  async function makeBlob(model) {
    const c = document.createElement("canvas");
    await drawCard(c, model);
    let b = await toBlob(c);
    if (!b) { await drawCard(c, { ...model, home: { ...model.home, logo: null }, away: { ...model.away, logo: null } }); b = await toBlob(c); }
    return b;
  }

  const api = { cardModel, makeBlob, drawCard };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniCard = api;
})(typeof window !== "undefined" ? window : globalThis);
