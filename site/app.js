/* Municipal en vivo: lee los JSON generados por scripts/build_site_data.py */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  let config = {};
  let data = { matches: null, standings: null, news: null, meta: null };
  let newsFeed = "municipal";
  let timer = null;

  // ---------- utilidades ----------
  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) {
      if (kid == null || kid === false) continue;
      node.append(kid.nodeType ? kid : document.createTextNode(kid));
    }
    return node;
  }
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
  const tz = () => config.timezone || "America/Guatemala";
  const fmt = (opts) => new Intl.DateTimeFormat("es-GT", { timeZone: tz(), ...opts });
  const fDay = (d) => fmt({ weekday: "short", day: "numeric", month: "short" }).format(d).replace(/\./g, "");
  const fDayLong = (d) => fmt({ weekday: "long", day: "numeric", month: "long" }).format(d);
  const fTime = (d) => fmt({ hour: "numeric", minute: "2-digit", hour12: true }).format(d).replace(/\s/g, " ");
  const compLabel = (c) => (config.competition_labels || {})[c] || c || "";
  const isMe = (side) => side.id === String(config.team_id) || side.name === config.team;

  function initials(name) {
    const words = (name || "").replace(/\b(FC|CD|GFC|MC|SC)\b/g, "").trim().split(/\s+/);
    return ((words[0] || "?")[0] + (words[1] ? words[1][0] : "")).toUpperCase();
  }
  function badge(side) {
    const b = el("span", { class: "badge", "aria-hidden": "true" });
    if (side.logo && /^https?:/.test(side.logo)) {
      const img = el("img", { src: side.logo, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
      img.addEventListener("error", () => { img.remove(); b.textContent = initials(side.name); });
      b.append(img);
    } else b.textContent = initials(side.name);
    return b;
  }
  function ago(iso) {
    const secs = (Date.parse(iso) - Date.now()) / 1000;
    if (!isFinite(secs)) return "";
    const rtf = new Intl.RelativeTimeFormat("es", { numeric: "auto" });
    const abs = Math.abs(secs);
    if (abs < 60) return "hace un momento";
    if (abs < 3600) return rtf.format(Math.round(secs / 60), "minute");
    if (abs < 86400) return rtf.format(Math.round(secs / 3600), "hour");
    if (abs < 86400 * 30) return rtf.format(Math.round(secs / 86400), "day");
    return fmt({ day: "numeric", month: "short", year: "numeric" }).format(new Date(iso));
  }
  async function getJson(name) {
    const res = await fetch(`data/${name}.json?t=${Math.floor(Date.now() / 60000)}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
    return res.json();
  }

  // ---------- partidos ----------
  const start = (m) => new Date(m.start);
  function split(matches) {
    const now = Date.now();
    const live = matches.filter((m) => m.state === "in");
    const upcoming = matches
      .filter((m) => m.state === "pre" && !m.postponed && start(m) > now - 3 * 3600e3)
      .sort((a, b) => start(a) - start(b));
    const results = matches.filter((m) => m.state === "post" && !m.postponed).sort((a, b) => start(b) - start(a));
    return { live, upcoming, results };
  }

  function countdown(m) {
    const ms = start(m) - Date.now();
    if (ms <= 0) return "Empieza en unos minutos";
    const mins = Math.floor(ms / 60000);
    const d = Math.floor(mins / 1440), h = Math.floor((mins % 1440) / 60), mi = mins % 60;
    const plural = (n, s, p) => `${n} ${n === 1 ? s : p}`;
    if (d >= 1) return `Faltan ${plural(d, "día", "días")} y ${plural(h, "hora", "horas")}`;
    if (h >= 1) return `Faltan ${plural(h, "hora", "horas")} y ${plural(mi, "minuto", "minutos")}`;
    return `Faltan ${plural(mi, "minuto", "minutos")}`;
  }

  function renderBoard() {
    const box = $("board");
    box.replaceChildren();
    const matches = (data.matches && data.matches.matches) || [];
    if (!matches.length) {
      box.append(el("p", { class: "board-msg", text: "Todavía no hay partidos para mostrar." }));
      return;
    }
    const { live, upcoming, results } = split(matches);
    const focus = live[0] || upcoming[0] || results[0];
    const next = !live[0] && upcoming[0] ? upcoming[0] : null;
    const d = start(focus);
    const home = focus.home, away = focus.away;

    let status, center;
    if (live[0]) {
      status = el("p", { class: "status live", text: `En vivo ${focus.clock || focus.status || ""}`.trim() });
      center = scoreDigits(focus);
    } else if (next) {
      status = el("p", { class: "status", text: "Próximo partido" });
      center = el("div", { class: "kickoff" }, el("span", { class: "hour", text: fTime(d) }), el("span", { class: "vs", text: "contra" }));
    } else {
      status = el("p", { class: "status", text: "Último resultado" });
      center = scoreDigits(focus);
    }
    box.append(
      status,
      el("div", { class: "score-row" },
        el("div", { class: "side" }, badge(home), el("span", { class: "nm", text: home.name })),
        center,
        el("div", { class: "side" }, badge(away), el("span", { class: "nm", text: away.name }))),
      el("p", { class: "where", text: [fDayLong(d), compLabel(focus.competition), focus.venue].filter(Boolean).join(", ") })
    );
    if (next) {
      const cd = el("p", { class: "countdown", id: "countdown", text: countdown(next) });
      box.append(cd);
    }
    if (!live[0] && !next && !upcoming.length) {
      box.append(el("p", { class: "where", text: "No hay más partidos programados por ahora." }));
    }
    const last = results[0];
    if ((live[0] || next) && last) {
      const r = last.result;
      box.append(el("p", { class: "last" },
        el("span", { text: "Último resultado:" }),
        el("strong", { text: `${last.home.name} ${last.home.score ?? "-"} - ${last.away.score ?? "-"} ${last.away.name}` }),
        r ? el("span", { class: `chip ${r}`, title: { G: "Ganó", E: "Empató", P: "Perdió" }[r], text: r }) : null));
    }
    box.dataset.next = next ? next.start : "";
  }
  function scoreDigits(m) {
    const s = (v) => (v == null ? "-" : v);
    return el("div", { class: "digits", "aria-label": `${s(m.home.score)} a ${s(m.away.score)}` },
      el("span", { text: s(m.home.score) }), el("span", { class: "sep", text: "-" }), el("span", { text: s(m.away.score) }));
  }

  function matchRow(m) {
    const showScore = m.state !== "pre";
    const row = (side) => el("div", { class: "t-row" },
      badge(side),
      el("span", { class: `n${isMe(side) ? " me" : ""}`, text: side.name }),
      el("span", { class: "s", text: showScore && side.score != null ? side.score : "" }));
    const d = start(m);
    const meta = [compLabel(m.competition), m.venue].filter(Boolean).join(", ");
    return el("li", null,
      el("a", { class: "m", href: safeUrl(m.url), target: "_blank", rel: "noopener" },
        el("div", { class: "when" }, el("span", { class: "d", text: fDay(d) }), el("span", { text: fTime(d) })),
        el("div", null, row(m.home), row(m.away), el("div", { class: "meta", text: meta })),
        m.result ? el("span", { class: `chip ${m.result}`, title: { G: "Ganó", E: "Empató", P: "Perdió" }[m.result], text: m.result }) : el("span")));
  }

  function renderMatches() {
    const matches = (data.matches && data.matches.matches) || [];
    const { live, upcoming, results } = split(matches);
    const up = $("upcoming"), res = $("results");
    up.replaceChildren(); res.replaceChildren();
    const coming = [...live, ...upcoming].slice(0, 6);
    if (coming.length) coming.forEach((m) => up.append(matchRow(m)));
    else up.append(el("li", { class: "empty", text: "No hay partidos programados por ahora." }));
    const done = results.slice(0, 8);
    if (done.length) done.forEach((m) => res.append(matchRow(m)));
    else res.append(el("li", { class: "empty", text: "Todavía no hay resultados." }));

    const form = $("form");
    const last5 = results.filter((m) => m.result).slice(0, 5).reverse();
    form.replaceChildren();
    if (last5.length) {
      form.hidden = false;
      form.append(el("span", { text: "Últimos partidos:" }),
        ...last5.map((m) => el("span", { class: `chip ${m.result}`, title: `${m.home.name} ${m.home.score}-${m.away.score} ${m.away.name}`, text: m.result })));
    } else form.hidden = true;
  }

  // ---------- tabla ----------
  function renderStandings() {
    const box = $("standings");
    box.replaceChildren();
    const s = data.standings;
    const groups = (s && s.groups) || [];
    if (!groups.length) {
      box.append(el("p", { class: "empty", text: "La tabla no está disponible en este momento. Se intentará de nuevo en la próxima actualización." }));
      return;
    }
    if (s.stale) box.append(el("p", { class: "stale", text: "Mostrando la última tabla guardada. ESPN no respondió en esta actualización." }));
    groups.forEach((g) => {
      const head = el("tr", null,
        el("th", { scope: "col", text: "#", "aria-label": "Posición" }),
        el("th", { scope: "col", text: "Equipo" }),
        el("th", { scope: "col", text: "PJ", title: "Partidos jugados" }),
        ...["G", "E", "P", "GF", "GC"].map((h) => el("th", { scope: "col", class: "opt", text: h, title: { G: "Ganados", E: "Empatados", P: "Perdidos", GF: "Goles a favor", GC: "Goles en contra" }[h] })),
        el("th", { scope: "col", text: "DG", title: "Diferencia de goles" }),
        el("th", { scope: "col", text: "Pts", title: "Puntos" }));
      const v = (x) => (x == null ? "-" : x);
      const rows = g.rows.map((r) => el("tr", { class: r.is_municipal ? "me" : null, "aria-current": r.is_municipal ? "true" : null },
        el("td", { text: r.pos }),
        el("td", null, el("span", { class: "team" }, badge({ logo: r.logo, name: r.name }), r.name)),
        el("td", { text: v(r.pj) }),
        ...["g", "e", "p", "gf", "gc"].map((k) => el("td", { class: "opt", text: v(r[k]) })),
        el("td", { text: r.dg > 0 ? `+${r.dg}` : v(r.dg) }),
        el("td", { class: "pts", text: v(r.pts) })));
      box.append(el("div", { class: "tablewrap" },
        el("table", { class: "std" },
          g.name ? el("caption", { text: g.name }) : null,
          el("thead", null, head), el("tbody", null, rows))));
    });
  }

  // ---------- noticias ----------
  function renderNews() {
    const list = $("news-list");
    list.replaceChildren();
    const items = (data.news && data.news[newsFeed]) || [];
    if (!items.length) {
      list.append(el("li", { class: "empty", text: "No hay noticias por ahora." }));
      return;
    }
    items.slice(0, 12).forEach((n) => list.append(el("li", null,
      el("a", { href: safeUrl(n.url), target: "_blank", rel: "noopener" },
        el("div", null,
          el("div", { class: "hl", text: n.title }),
          n.summary ? el("p", { class: "sum", text: n.summary }) : null,
          el("div", { class: "src", text: [n.source, n.published ? ago(n.published) : ""].filter(Boolean).join(", ") })),
        n.image && /^https?:/.test(n.image) ? el("img", { src: n.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" }) : el("span")))));
  }
  document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
    newsFeed = b.dataset.feed;
    document.querySelectorAll(".seg button").forEach((x) => {
      x.setAttribute("aria-selected", String(x === b));
      x.tabIndex = x === b ? 0 : -1;
    });
    $("news-list").setAttribute("aria-labelledby", b.id);
    renderNews();
  }));

  // ---------- redes ----------
  let socialBuilt = false;
  function renderSocial() {
    if (socialBuilt) return;
    socialBuilt = true;
    const box = $("social");
    const x = config.x_handle, ig = config.instagram_handle;
    if (x) {
      const frame = el("div", { class: "frame", id: "x-frame" });
      box.append(el("div", null, el("h3", { text: `X (@${x})` }), frame,
        el("a", { class: "btn", href: `https://x.com/${encodeURIComponent(x)}`, target: "_blank", rel: "noopener", text: "Abrir en X" })));
      if (config.show_x_embed !== false) lazy(frame, () => {
        frame.append(el("a", { class: "twitter-timeline", "data-height": "520", "data-lang": "es",
          "data-theme": matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
          "data-chrome": "noheader nofooter transparent", href: `https://twitter.com/${encodeURIComponent(x)}`, text: `Posts de @${x}` }));
        const s = el("script", { src: "https://platform.twitter.com/widgets.js", async: true, charset: "utf-8" });
        document.body.append(s);
      });
    }
    if (ig) {
      const frame = el("div", { class: "frame" });
      box.append(el("div", null, el("h3", { text: `Instagram (@${ig})` }), frame,
        el("a", { class: "btn", href: `https://www.instagram.com/${encodeURIComponent(ig)}/`, target: "_blank", rel: "noopener", text: "Abrir en Instagram" })));
      if (config.show_instagram_embed !== false) lazy(frame, () => {
        frame.append(el("iframe", { src: `https://www.instagram.com/${encodeURIComponent(ig)}/embed`, title: `Publicaciones de @${ig} en Instagram`, loading: "lazy", scrolling: "no" }));
      });
    }
  }
  function lazy(node, fn) {
    if (!("IntersectionObserver" in window)) return fn();
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { io.disconnect(); fn(); }
    }, { rootMargin: "300px" });
    io.observe(node);
  }

  // ---------- calendario y pie ----------
  function renderSubscribe() {
    const ics = new URL("municipal.ics", location.href);
    const web = "webcal://" + ics.host + ics.pathname;
    const links = [
      ["Google Calendar", `https://calendar.google.com/calendar/render?cid=${encodeURIComponent(web)}`],
      ["Outlook", `https://outlook.live.com/calendar/0/addfromweb?url=${encodeURIComponent(ics.href)}&name=Municipal`],
      ["iPhone y Mac", web],
      ["Archivo .ics", ics.href],
    ];
    const ul = $("subscribe-links");
    ul.replaceChildren(...links.map(([t, h]) => el("li", null, el("a", { href: h, text: t }))));
  }
  function renderFooter() {
    const meta = data.meta;
    const p = $("updated");
    if (meta && meta.updated) {
      const bad = Object.entries(meta.sources || {}).filter(([, v]) => v !== "ok").map(([k]) => k);
      p.textContent = `Actualizado ${ago(meta.updated)}, con datos de ESPN y Google Noticias.` +
        (bad.length ? ` Sin respuesta en la última actualización: ${bad.join(", ")}.` : "");
    }
  }

  // ---------- ciclo ----------
  function tickCountdown() {
    const c = $("countdown"), box = $("board");
    if (!c || !box.dataset.next) return;
    const m = (data.matches.matches || []).find((x) => x.start === box.dataset.next);
    if (m) c.textContent = countdown(m);
  }
  async function load() {
    const names = ["matches", "standings", "news", "meta"];
    const res = await Promise.allSettled(names.map(getJson));
    names.forEach((n, i) => { if (res[i].status === "fulfilled") data[n] = res[i].value; });
    if (res[0].status === "rejected" && !data.matches) {
      $("board").replaceChildren(el("p", { class: "board-msg", text: "No se pudieron cargar los partidos. Recarga la página en unos minutos." }));
    } else {
      renderBoard(); renderMatches();
    }
    renderStandings(); renderNews(); renderFooter();
    schedule();
  }
  function schedule() {
    clearTimeout(timer);
    const live = data.matches && data.matches.matches.some((m) => m.state === "in");
    timer = setTimeout(load, live ? 45e3 : 180e3);
  }

  async function init() {
    try { config = await (await fetch("config.json", { cache: "no-store" })).json(); } catch (_) { config = {}; }
    config.team = config.team || "Municipal";
    config.team_id = config.team_id || "7258";
    renderSubscribe();
    renderSocial();
    await load();
    setInterval(tickCountdown, 30e3);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) load(); });
  }
  init();
})();
