/* Municipal en vivo: lee los JSON generados por scripts/build_site_data.py */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const BASE_TITLE = document.title;
  let config = {};
  let data = { matches: null, standings: null, news: null, meta: null, players: null, roster: null };
  let newsFeed = "municipal";
  let showAllPlayers = false;
  let playersView = "squad";
  let squadGroup = null;      // pestaña de posición abierta en el plantel   // "squad" (fichas del plantel) o "stats" (tabla)
  let playerComp = "all";
  let timer = null;

  // ---------- utilidades ----------
  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (typeof v === "function") node.addEventListener(k.replace(/^on/, ""), v);
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
  const RESULT = { G: "Ganó", E: "Empató", P: "Perdió" };

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
  const chip = (r) => el("span", { class: `chip ${r}`, title: RESULT[r], text: r });
  const matchHref = (m) => (m.detail ? `#/partido/${m.id}` : safeUrl(m.url));

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

  function scoreDigits(m) {
    const s = (v) => (v == null ? "-" : v);
    return el("div", { class: "digits", "aria-label": `${s(m.home.score)} a ${s(m.away.score)}` },
      el("span", { text: s(m.home.score) }), el("span", { class: "sep", text: "-" }), el("span", { text: s(m.away.score) }));
  }

  // Marcador de un partido (portada y página del partido).
  function fillBoard(box, m) {
    const d = start(m);
    let status, center;
    if (m.postponed) {
      status = el("p", { class: "status", text: "Partido aplazado" });
      center = el("div", { class: "kickoff" }, el("span", { class: "vs", text: "contra" }));
    } else if (m.state === "in") {
      status = el("p", { class: "status live", text: `En vivo ${m.clock || m.status || ""}`.trim() });
      center = scoreDigits(m);
    } else if (m.state === "pre") {
      status = el("p", { class: "status", text: "Próximo partido" });
      center = el("div", { class: "kickoff" }, el("span", { class: "hour", text: fTime(d) }), el("span", { class: "vs", text: "contra" }));
    } else {
      status = el("p", { class: "status", text: "Resultado final" });
      center = scoreDigits(m);
    }
    box.replaceChildren(status,
      el("div", { class: "score-row" },
        el("div", { class: "side" }, badge(m.home), el("span", { class: "nm", text: m.home.name })),
        center,
        el("div", { class: "side" }, badge(m.away), el("span", { class: "nm", text: m.away.name }))),
      el("p", { class: "where", text: [fDayLong(d), compLabel(m.competition), m.venue].filter(Boolean).join(", ") }),
      m.state !== "post" && m.broadcasts && m.broadcasts.length
        ? el("p", { class: "where tv", text: `Dónde verlo: ${m.broadcasts.join(", ")}` }) : "");
  }

  function renderBoard() {
    const box = $("board");
    const matches = (data.matches && data.matches.matches) || [];
    if (!matches.length) {
      box.replaceChildren(el("p", { class: "board-msg", text: "Todavía no hay partidos para mostrar." }));
      return;
    }
    const { live, upcoming, results } = split(matches);
    const focus = live[0] || upcoming[0] || results[0];
    const next = !live[0] && upcoming[0] && upcoming[0] === focus ? focus : null;
    fillBoard(box, focus);
    if (next && !next.postponed) box.append(el("p", { class: "countdown", id: "countdown", text: countdown(next) }));
    if (focus.detail) box.append(el("p", { class: "board-link" }, el("a", { href: `#/partido/${focus.id}`, text: "Ver el partido" })));
    if (!live[0] && !upcoming.length) box.append(el("p", { class: "where", text: "No hay más partidos programados por ahora." }));
    const last = results[0];
    if (focus !== last && last) {
      box.append(el("p", { class: "last" },
        el("span", { text: "Último resultado:" }),
        el("strong", { text: `${last.home.name} ${last.home.score ?? "-"} - ${last.away.score ?? "-"} ${last.away.name}` }),
        last.result ? chip(last.result) : null));
    }
    const recent = results.filter((m) => m.result).slice(0, 5).reverse();
    if (recent.length) {
      box.append(el("p", { class: "streak", "aria-label": `Últimos ${recent.length} partidos` },
        el("span", { text: "Últimos partidos" }), ...recent.map((x) => chip(x.result))));
    }
    box.dataset.next = next ? next.start : "";
  }

  function forecastCard(m) {
    const F = window.MuniForecast;
    const g = data.standings && data.standings.groups && data.standings.groups[0];
    if (!F || !g || !m || m.state !== "pre" || m.postponed || (m.slug && m.slug !== "gua.1")) return null;
    const f = F.forecast(g.rows, m.home.id, m.away.id);
    if (!f) return null;
    const r0 = (n) => `${Math.round(n)}%`;
    const bar = el("div", { class: "fc-bar", role: "img",
      "aria-label": `${m.home.name} ${r0(f.pHome)}, empate ${r0(f.pDraw)}, ${m.away.name} ${r0(f.pAway)}` },
      el("span", { class: isMe(m.home) ? "w me" : "w", style: `width:${f.pHome}%` }),
      el("span", { class: "d", style: `width:${f.pDraw}%` }),
      el("span", { class: isMe(m.away) ? "l me" : "l", style: `width:${f.pAway}%` }));
    return el("div", { class: "forecast" },
      el("h3", { text: "Pronóstico del partido" }),
      el("div", { class: "fc-nums" },
        el("span", null, el("strong", { text: r0(f.pHome) }), ` gana ${m.home.name}`),
        el("span", null, el("strong", { text: r0(f.pDraw) }), " empate"),
        el("span", null, el("strong", { text: r0(f.pAway) }), ` gana ${m.away.name}`)),
      bar,
      el("p", { class: "fc-scores" }, "Marcadores más probables: ",
        ...f.topScores.map((s) => el("span", { class: "chip-s", text: `${s.home}-${s.away} (${r0(s.p)})` }))),
      el("p", { class: "liga-help", text: "Estimación con los goles a favor y en contra de cada equipo en el torneo y ventaja de local. No considera lesiones ni alineaciones. Son probabilidades, no pronósticos seguros." }));
  }

  /** "Cómo llegan": los dos equipos lado a lado con los datos que ya tenemos (tabla, últimos partidos, goleadores). */
  function previaBlock(m, rival) {
    const P = window.MuniPrevia;
    if (!P || m.state !== "pre" || m.postponed) return null;
    const g = data.standings && data.standings.groups && data.standings.groups[0];
    const league = !m.slug || m.slug === "gua.1";
    const cmp = league && g ? P.compare(g.rows, m.home.id, m.away.id) : null;
    const matches = (data.matches && data.matches.matches) || [];
    const formOf = (side) => (isMe(side) ? P.recentForm(matches, side.id, 5)
      : rival && String(rival.team_id) === String(side.id) ? (rival.form || []) : []);
    const forms = [formOf(m.home), formOf(m.away)];
    const mine = isMe(m.home) || isMe(m.away);
    const scorers = mine ? P.topScorers((data.players && data.players.players) || [], 3) : [];
    const words = cmp ? P.headline(cmp) : [];
    if (!cmp && !forms[0].length && !forms[1].length && !scorers.length) return null;

    const team = (side) => el("div", { class: "pv-team" }, badge(side), el("strong", { class: isMe(side) ? "me" : "", text: side.name }));
    const formCol = (list) => el("div", { class: "pv-form" }, list.length
      ? list.map((f) => el("span", { class: `chip ${f.result}`, title: `${f.home ? "Local" : "Visitante"} contra ${f.vs}, ${f.score}`, text: f.result }))
      : el("span", { class: "meta", text: "Sin datos" }));
    const kids = [el("div", { class: "pv-head" }, team(m.home), el("span", { class: "pv-vs", text: "vs" }), team(m.away))];
    if (words.length) kids.push(el("p", { class: "pv-words", text: words.join(" ") }));
    const grid = [];
    if (cmp) {
      cmp.rows.forEach((r) => grid.push(
        el("span", { class: `pv-v${r.better === "a" ? " best" : ""}`, text: r.a }),
        el("span", { class: "pv-l", text: r.label }),
        el("span", { class: `pv-v${r.better === "b" ? " best" : ""}`, text: r.b })));
    }
    if (forms[0].length || forms[1].length) {
      grid.push(formCol(forms[0]), el("span", { class: "pv-l", text: "Últimos 5 partidos" }), formCol(forms[1]));
    }
    if (grid.length) kids.push(el("div", { class: "pv-grid" }, ...grid));
    if (scorers.length) {
      kids.push(el("div", { class: "pv-scorers" }, el("h3", { text: "Goleadores de Municipal" }),
        el("ul", { class: "plain" }, ...scorers.map((p) => el("li", null, el("strong", { text: p.name }),
          el("span", { class: "meta", text: ` ${p.goals} ${p.goals === 1 ? "gol" : "goles"}` }))))));
    }
    const fc = forecastCard(m);
    if (fc) kids.push(fc);
    return section("Cómo llegan", ...kids);
  }

  function matchRow(m) {
    const showScore = m.state !== "pre";
    const row = (side) => el("div", { class: "t-row" },
      badge(side),
      el("span", { class: `n${isMe(side) ? " me" : ""}`, text: side.name }),
      el("span", { class: "s", text: showScore && side.score != null ? side.score : "" }));
    const d = start(m);
    const meta = [m.postponed ? "Aplazado" : "", compLabel(m.competition), m.venue].filter(Boolean).join(", ");
    const internal = m.detail;
    return el("li", null,
      el("a", { class: `m${m.result ? ` r-${m.result}` : ""}${m.state === "in" ? " live" : ""}`, href: matchHref(m), target: internal ? null : "_blank", rel: internal ? null : "noopener" },
        el("div", { class: "when" }, el("span", { class: "d", text: fDay(d) }), el("span", { text: fTime(d) })),
        el("div", null, row(m.home), row(m.away), el("div", { class: "meta", text: meta })),
        m.result ? chip(m.result) : el("span")));
  }

  function renderMatches() {
    const matches = (data.matches && data.matches.matches) || [];
    const { live, upcoming, results } = split(matches);
    const up = $("upcoming"), res = $("results");
    const fc = $("forecast");
    fc.replaceChildren();
    const nextLeague = [...live, ...upcoming].find((m) => m.state === "pre" && !m.postponed && (!m.slug || m.slug === "gua.1"));
    const card = nextLeague && forecastCard(nextLeague);
    if (card) fc.append(card);
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
      const lg = ligaOpts();
      const zone = (r) => (g !== groups[0] || !r.pos ? "" : r.pos <= lg.direct ? " z-dir" : r.pos <= lg.qualify ? " z-pre" : "");
      const rows = g.rows.map((r) => el("tr", { class: (r.is_municipal ? "me" : "") + zone(r) || null, "aria-current": r.is_municipal ? "true" : null },
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
    box.append(el("p", { class: "legend" },
      el("span", { class: "lg dir", text: "1.º y 2.º: directo a semifinales" }),
      el("span", { class: "lg pre", text: "3.º al 6.º: ronda previa" })));
    const g0 = data.standings && data.standings.groups && data.standings.groups[0];
    if (window.MuniShare && g0 && g0.rows.length) {
      const lg = ligaOpts();
      box.append(el("p", { class: "actions" }, waButton(window.MuniShare.tableText(g0.rows, {
        qualify: lg.qualify, tournament: (config.liguilla && config.liguilla.tournament) || "", url: siteUrl() + "#tabla" }), "Compartir la tabla por WhatsApp")));
    }
  }

  // ---------- liguilla ----------
  let ligaPicks = {};
  function ligaOpts() {
    const c = config.liguilla || {};
    return { rounds: c.regular_rounds || 22, direct: c.direct || 2, qualify: c.qualify || 6 };
  }
  const siteUrl = () => location.origin + location.pathname;
  function waButton(text, label) {
    const SH = window.MuniShare;
    if (!SH) return null;
    return el("a", { class: "btn btn-wa", href: SH.whatsappUrl(text), target: "_blank", rel: "noopener noreferrer", text: label || "Compartir por WhatsApp" });
  }
  const pct = (n) => (n == null ? "-" : n > 99 && n < 100 ? ">99%" : n < 1 && n > 0 ? "<1%" : `${Math.round(n)}%`);
  function renderOdds(od) {
    const list = od.teams.slice().sort((a, b) => b.p_qualify - a.p_qualify || a.pos - b.pos);
    const modes = { calendario: "con el calendario de la liga", mixto: "con el calendario de la liga y partidos sin fecha repartidos al azar",
      aleatorio: "con los partidos que faltan repartidos al azar entre los equipos" };
    return el("div", { class: "odds" },
      el("h3", { text: "Probabilidad de clasificar" }),
      el("p", { class: "legend" },
        el("span", { class: "lg dir", text: "Directo a semifinales" }),
        el("span", { class: "lg pre", text: "Clasifica (top 6)" })),
      el("ol", { class: "odds-list" }, ...list.map((t) => el("li", { class: t.is_municipal ? "me" : null },
        el("span", { class: "o-team" }, badge({ logo: t.logo, name: t.name }), el("span", { class: "o-name", text: t.name })),
        el("span", { class: "o-bar", role: "img", "aria-label": `${t.name}: ${pct(t.p_qualify)} de clasificar, ${pct(t.p_direct)} directo` },
          el("span", { class: "o-q", style: `width:${t.p_qualify}%` }), el("span", { class: "o-d", style: `width:${t.p_direct}%` })),
        el("span", { class: "o-pct", text: pct(t.p_qualify) })))),
      el("p", { class: "liga-help", text: `Estimación con ${od.sims.toLocaleString("es-GT")} simulaciones del resto de la fase regular, ${modes[od.fixtures] || ""}. Cada equipo pesa según sus goles a favor y en contra, con ventaja de local. No considera lesiones, refuerzos ni suspensiones, y el desempate es por diferencia de goles. Son probabilidades, no pronósticos.${od.updated ? ` Calculadas ${ago(od.updated)}; se recalculan en cada actualización del sitio.` : ""}` }));
  }
  /** Partidos con fecha que les faltan a los equipos que pelean por la liguilla y qué tan difíciles son. */
  function renderSchedule(od, o) {
    const byId = Object.fromEntries(od.teams.map((t) => [t.team_id, t]));
    const withSos = od.teams.filter((t) => t.sos != null);
    if (od.fixtures === "aleatorio" || !withSos.length) return null;
    const shown = od.teams.filter((t) => t.pos <= o.qualify + 2 && (t.fixtures || []).length).sort((a, b) => a.pos - b.pos);
    if (!shown.length) return null;
    const tag = (t) => {
      const r = t.sos_rank, n = withSos.length;
      return r <= n / 3 ? ["Difícil", "hard"] : r > 2 * n / 3 ? ["Fácil", "easy"] : ["Medio", "mid"];
    };
    return el("details", { class: "subscribe sched" },
      el("summary", { text: "Calendario que les falta a los equipos de arriba" }),
      el("ol", { class: "sched-list" }, ...shown.map((t) => {
        const [label, cls] = tag(t);
        return el("li", { class: t.is_municipal ? "me" : null },
          el("div", { class: "sched-head" }, el("strong", { text: `${t.pos}.º ${t.name}` }), el("span", { class: `diff ${cls}`, text: label })),
          el("p", { class: "sched-opps" }, ...t.fixtures.map((f) => el("span", { class: "chip-s", text: `${f.home ? "Local" : "Visita"}: ${(byId[f.opp] || {}).name || "?"}` }))));
      })),
      el("p", { class: "liga-help", text: "Solo incluye los partidos con fecha en el calendario de la liga. La dificultad compara el promedio de puntos por partido de los rivales que les faltan: más alto, más difícil." }));
  }
  const SVGNS = "http://www.w3.org/2000/svg";
  const sv = (tag, attrs, ...kids) => {
    const n = document.createElementNS(SVGNS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => n.setAttribute(k, v));
    kids.forEach((k) => n.append(k));
    return n;
  };
  /** Cómo cambia con el tiempo la probabilidad de Municipal de clasificar (y de pasar directo). */
  function renderRace(h) {
    const es = (h && h.entries) || [];
    const box = el("div", { class: "race" }, el("h3", { text: "Carrera a la liguilla" }));
    if (es.length < 2) {
      box.append(el("p", { class: "liga-help", text: "La gráfica se irá llenando: el sitio guarda la probabilidad de Municipal en cada actualización y la dibuja jornada tras jornada." }));
      return box;
    }
    const W = 640, H = 240, m = { l: 40, r: 100, t: 14, b: 30 };
    const n = es.length;
    const X = (i) => m.l + i * (W - m.l - m.r) / (n - 1);
    const Y = (p) => m.t + (100 - p) * (H - m.t - m.b) / 100;
    const when = (e) => fmt({ day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(new Date(e.t));
    const series = [
      { key: "p_qualify", label: "Clasifica", cls: "s1" },
      { key: "p_direct", label: "Directo a semifinales", cls: "s2" },
    ];
    box.append(el("p", { class: "legend" }, ...series.map((s) => el("span", { class: `lg ${s.cls}`, text: s.label }))));

    const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, class: "race-svg", role: "img",
      "aria-label": `Probabilidad de Municipal de clasificar a la liguilla en ${n} actualizaciones. Última: ${pct(es[n - 1].p_qualify)} de clasificar y ${pct(es[n - 1].p_direct)} de pasar directo.` });
    [0, 50, 100].forEach((v) => {
      svg.append(sv("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: "grid" }));
      const t = sv("text", { x: m.l - 6, y: Y(v) + 4, class: "tick", "text-anchor": "end" }); t.textContent = `${v}%`; svg.append(t);
    });
    const step = Math.max(1, Math.ceil(n / 6));
    es.forEach((e, i) => {
      if (i % step && i !== n - 1) return;
      const t = sv("text", { x: X(i), y: H - 8, class: "tick", "text-anchor": i === 0 ? "start" : i === n - 1 ? "end" : "middle" });
      t.textContent = `PJ ${e.pj}`; svg.append(t);
    });
    const ends = [];
    series.forEach((s) => {
      svg.append(sv("polyline", { points: es.map((e, i) => `${X(i).toFixed(1)},${Y(e[s.key]).toFixed(1)}`).join(" "), class: `line ${s.cls}` }));
      es.forEach((e, i) => { if (n <= 24 || i === n - 1) svg.append(sv("circle", { cx: X(i), cy: Y(e[s.key]), r: 4, class: `dot ${s.cls}` })); });
      ends.push({ y: Y(es[n - 1][s.key]), s });
    });
    ends.sort((a, b) => a.y - b.y);
    if (ends.length > 1 && ends[1].y - ends[0].y < 14) ends[0].y = ends[1].y - 14; // etiquetas sin encimarse
    ends.forEach(({ y, s }) => {
      const t = sv("text", { x: X(n - 1) + 10, y: y + 4, class: "end-label" });
      t.textContent = `${s.label.split(" ")[0]} ${pct(es[n - 1][s.key])}`; svg.append(t);
    });

    // hover: línea guía + tooltip con el punto más cercano
    const cross = sv("line", { y1: m.t, y2: H - m.b, class: "cross", visibility: "hidden" });
    const hit = sv("rect", { x: m.l - 10, y: 0, width: W - m.l - m.r + 20, height: H, fill: "transparent" });
    svg.append(cross, hit);
    const tip = el("div", { class: "race-tip", hidden: true });
    const show = (ev) => {
      const r = svg.getBoundingClientRect();
      const px = (ev.clientX - r.left) / r.width * W;
      const i = Math.max(0, Math.min(n - 1, Math.round((px - m.l) / ((W - m.l - m.r) / (n - 1)))));
      const e = es[i];
      cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.setAttribute("visibility", "visible");
      tip.replaceChildren(el("strong", { text: when(e) }),
        el("span", { text: `${e.pos}.º lugar, ${e.pts} pts, ${e.pj} partidos` }),
        el("span", { text: `Clasifica: ${pct(e.p_qualify)}` }), el("span", { text: `Directo: ${pct(e.p_direct)}` }));
      tip.hidden = false;
      const left = X(i) / W * 100;
      tip.style.left = `${Math.min(Math.max(left, 18), 82)}%`;
    };
    const hide = () => { tip.hidden = true; cross.setAttribute("visibility", "hidden"); };
    hit.addEventListener("pointermove", show); hit.addEventListener("pointerdown", show);
    hit.addEventListener("pointerleave", hide);
    box.append(el("div", { class: "race-chart" }, svg, tip));

    const rows = es.map((e) => el("tr", null, el("td", { text: when(e) }), el("td", { text: `${e.pos}.º` }), el("td", { text: e.pts }),
      el("td", { text: e.pj }), el("td", { text: pct(e.p_qualify) }), el("td", { text: pct(e.p_direct) })));
    box.append(el("details", { class: "subscribe" }, el("summary", { text: "Ver los datos en tabla" }),
      el("div", { class: "tablewrap" }, el("table", { class: "std" },
        el("thead", null, el("tr", null, ...["Fecha", "Pos", "Pts", "PJ", "Clasifica", "Directo"].map((t) => el("th", { scope: "col", text: t })))),
        el("tbody", null, ...rows.reverse())))));
    return box;
  }
  const STATUS = {
    direct: "Semifinales asegurada", qualified: "Liguilla asegurada", alive: "En disputa",
    "no-direct": "Sin directo posible", out: "Eliminado", unknown: "",
  };
  /** Los datos de Municipal en la liguilla, en grande: posición, puntos, probabilidades y partidos que faltan. */
  function ligaTiles(rows, o, me, pr) {
    const L = window.MuniLiguilla;
    const mine = L.situation(rows, o).find((t) => t.is_municipal || String(t.team_id) === String(config.team_id));
    if (!mine) return null;
    const zone = mine.pos <= o.direct ? "Directo a semifinales" : mine.pos <= o.qualify ? "Dentro de los 6" : "Fuera de los 6";
    const tile = (label, value, sub, extra) => el("div", { class: `tile${extra || ""}` },
      el("span", { class: "tile-l", text: label }), el("strong", { class: "tile-v", text: value }), sub ? el("span", { class: "tile-s", text: sub }) : null);
    const ring = (label, n, sub) => el("div", { class: "tile ring-tile" },
      el("div", { class: "ring", style: `--p:${Math.max(0, Math.min(100, Math.round(n)))}`, role: "img", "aria-label": `${label}: ${pct(n)}` },
        el("strong", { text: pct(n) })),
      el("span", { class: "tile-l", text: label }), el("span", { class: "tile-s", text: sub }));
    const list = [
      tile("Posición", `${mine.pos}.º`, zone, " first"),
      tile("Puntos", mine.pts == null ? "-" : mine.pts, mine.pj == null ? "" : `en ${mine.pj} partidos`),
      me && !pr.done ? ring("Clasifica", me.p_qualify, "a la liguilla") : null,
      me && !pr.done ? ring("Directo", me.p_direct, "a semifinales") : null,
      mine.left == null ? null : tile(mine.left === 1 ? "Falta" : "Faltan", mine.left, mine.left === 1 ? "partido" : "partidos"),
    ];
    return el("div", { class: "tiles" }, ...list);
  }

  function renderLiguilla() {
    const box = $("liga-box");
    box.replaceChildren();
    const L = window.MuniLiguilla, o = ligaOpts();
    const g = data.standings && data.standings.groups && data.standings.groups[0];
    const rows = g ? g.rows.filter((r) => r.pos).sort((a, b) => a.pos - b.pos) : [];
    if (!L || rows.length < o.qualify) {
      box.append(el("p", { class: "empty", text: "La llave aparecerá cuando la tabla esté disponible." }));
      return;
    }
    const pr = L.progress(rows, o);
    const name = (config.liguilla && config.liguilla.tournament) || "Apertura";
    box.append(el("p", { class: "liga-intro", text: pr.done
      ? `La fase regular del ${name} terminó. Esta es la llave real.`
      : `Así quedaría la liguilla del ${name} si la fase regular terminara hoy. Termina cuando todos hayan jugado ${pr.rounds} partidos: ${pr.minPJ === pr.maxPJ ? `hoy todos van en ${pr.minPJ}` : `hoy van entre ${pr.minPJ} y ${pr.maxPJ}`}, y faltan ${pr.matchesLeft} partidos en total. Es una simulación con la tabla actual y puede cambiar en cada jornada.` }));
    const sum = L.summary(rows, config.team_id, o);
    const od = data.odds && data.odds.teams && data.odds.teams.length ? data.odds : null;
    const me = od && od.teams.find((t) => t.is_municipal);
    if (me && !pr.done) sum.push(`Según la simulación, ${me.name} tiene ${pct(me.p_qualify)} de probabilidad de clasificar a la liguilla y ${pct(me.p_direct)} de pasar directo a semifinales.`);
    const shareLiga = window.MuniShare && sum.length ? el("p", { class: "actions" }, waButton(window.MuniShare.ligaText(sum, me, {
      tournament: (config.liguilla && config.liguilla.tournament) || "", url: siteUrl() + "#liguilla" }), "Compartir la liguilla por WhatsApp")) : null;
    const tiles = ligaTiles(rows, o, me, pr);
    if (tiles) box.append(tiles);
    if (sum.length) box.append(el("details", { class: "liga-more" }, el("summary", { text: "Ver el detalle en palabras" }),
      el("ul", { class: "liga-sum" }, ...sum.map((t) => el("li", { text: t })))), shareLiga);

    // llave interactiva
    const b = L.bracket(rows, ligaPicks, o);
    ligaPicks = b.picks;
    const side = (t, tieObj, n) => {
      if (!t) return el("div", { class: "lt empty" }, el("span", { class: "lt-name", text: tieObj.labels[n] || "Por definir" }));
      const won = tieObj.winner === t, lost = tieObj.winner && !won;
      const btn = el("button", { type: "button", class: `lt${won ? " won" : ""}${lost ? " lost" : ""}${t.is_municipal ? " me" : ""}`,
        "aria-pressed": won ? "true" : "false", title: "Avanzar a este equipo",
        onclick: () => { ligaPicks = { ...ligaPicks, [tieObj.id]: won ? undefined : t.seed }; renderLiguilla(); } },
        el("span", { class: "lt-seed", text: t.seed }), badge({ logo: t.logo, name: t.name }), el("span", { class: "lt-name", text: t.name }));
      return btn;
    };
    const wrap = el("div", { class: "bracket" });
    b.rounds.forEach((r, ri) => {
      const list = el("div", { class: "br-ties" });
      r.ties.forEach((t) => {
        // ida en casa del peor ubicado; vuelta en casa del mejor ubicado
        const note = t.hi && t.lo ? `Ida: ${t.lo.name}. Vuelta: ${t.hi.name}.` : "";
        list.append(el("div", { class: "tie" }, side(t.hi, t, 0), side(t.lo, t, 1), note ? el("p", { class: "tie-note", text: note }) : null));
      });
      wrap.append(el("div", { class: `br-round r${ri}` }, el("h3", { text: r.name }), list));
    });
    wrap.append(el("div", { class: "br-round r3" }, el("h3", { text: "Campeón" }),
      el("div", { class: "br-ties" }, el("div", { class: `trophy${b.champion ? " has" : ""}` },
        b.champion ? [badge({ logo: b.champion.logo, name: b.champion.name }), el("strong", { text: b.champion.name })] : el("span", { text: "Por definir" })))));
    box.append(el("p", { class: "br-hint", text: "Desliza para ver toda la llave →" }));
    box.append(el("div", { class: "bracket-wrap", tabindex: "0", role: "group", "aria-label": "Llave de la liguilla" }, wrap));
    box.append(el("p", { class: "liga-help", text: "Toca un equipo para avanzarlo en la llave y ver cómo se arma el camino al título." }),
      Object.keys(ligaPicks).some((k) => ligaPicks[k] != null)
        ? el("button", { type: "button", class: "btn small", text: "Reiniciar llave", onclick: () => { ligaPicks = {}; renderLiguilla(); } }) : null);

    if (od && !pr.done) box.append(renderOdds(od));
    box.append(renderRace(data.history));
    if (od && !pr.done) { const sc = renderSchedule(od, o); if (sc) box.append(sc); }

    // situación de cada equipo
    const st = L.situation(rows, o);
    const oddsOf = Object.fromEntries(((data.odds && data.odds.teams) || []).map((t) => [t.team_id, t]));
    const hasOdds = Object.keys(oddsOf).length > 0 && !pr.done;
    const th = (text, title) => el("th", { scope: "col", text, title: title || null });
    const head = el("tr", null, th("#"), th("Equipo"), th("Pts"), th("PJ", "Partidos jugados"),
      th("Faltan", "Partidos por jugar"), th("Máx.", "Máximo de puntos posibles"),
      hasOdds ? th("Clasifica", "Probabilidad de entrar al top 6") : null,
      hasOdds ? th("Directo", "Probabilidad de pasar directo a semifinales") : null, th("Situación"));
    const body = st.map((t) => el("tr", { class: t.is_municipal ? "me" : null },
      el("td", { text: t.pos }),
      el("td", null, el("span", { class: "team" }, badge({ logo: t.logo, name: t.name }), el("span", { text: t.name }))),
      el("td", { class: "pts", text: t.pts == null ? "-" : t.pts }),
      el("td", { text: t.pj == null ? "-" : t.pj }),
      el("td", { text: t.left == null ? "-" : t.left }),
      el("td", { text: t.max == null ? "-" : t.max }),
      hasOdds ? el("td", { class: "pts", text: oddsOf[t.team_id] ? pct(oddsOf[t.team_id].p_qualify) : "-" }) : null,
      hasOdds ? el("td", { text: oddsOf[t.team_id] ? pct(oddsOf[t.team_id].p_direct) : "-" }) : null,
      el("td", { class: `sit ${t.status}`, text: STATUS[t.status] || "" })));
    box.append(el("details", { class: "subscribe" }, el("summary", { text: "Qué necesita cada equipo" }),
      el("p", { class: "scroll-hint", text: "Desliza la tabla hacia los lados para ver todas las columnas →" }),
      el("div", { class: "tablewrap", tabindex: "0", role: "group", "aria-label": "Qué necesita cada equipo" }, el("table", { class: "std need" }, el("thead", null, head), el("tbody", null, body))),
      el("p", { class: "liga-help", text: "La situación se calcula con puntos: un empate en puntos con otro equipo se cuenta como posible, porque el desempate lo define la liga. Las series se simulan a ida y vuelta; el mejor ubicado cierra de local." })));
  }

  // ---------- jugadores ----------
  const ZERO_STATS = { pj: 0, starts: 0, goals: 0, assists: 0, yellow: 0, red: 0 };

  function playerCard(r, st) {
    const photo = el("span", { class: "pc-photo", "aria-hidden": "true" });
    if (r.photo && /^https?:/.test(r.photo)) {
      const img = el("img", { src: r.photo, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
      img.addEventListener("error", () => { img.remove(); photo.textContent = r.jersey || initials(r.name); });
      photo.append(img);
    } else photo.textContent = r.jersey || initials(r.name);
    const bits = [r.age ? `${r.age} años` : "", r.country].filter(Boolean).join(", ");
    const played = st.pj || st.goals || st.assists;
    const stat = (n, label) => el("div", { title: label }, el("strong", { text: n }), el("span", { text: label }));
    return el("li", { class: `pcard${r.injury ? " hurt" : ""}` },
      photo,
      el("div", { class: "pc-id" },
        el("strong", { class: "pc-name", text: r.name }),
        el("span", { class: "meta", text: bits }),
        r.injury ? el("span", { class: "pc-hurt", text: `Lesión: ${r.injury}` }) : null),
      played ? el("div", { class: "pc-stats" }, stat(st.pj, "PJ"), stat(st.goals, "G"), stat(st.assists, "A"))
        : el("span", { class: "pc-none", text: "Sin partidos" }));
  }

  function squadView(roster) {
    const list = roster.players || [];
    const ages = list.map((r) => r.age).filter(Boolean);
    const foreign = list.filter((r) => r.country && r.country !== "Guatemala").length;
    const facts = [`${list.length} jugadores`,
      ages.length ? `edad promedio ${(ages.reduce((a, n) => a + n, 0) / ages.length).toFixed(1)} años` : "",
      foreign ? `${foreign} ${foreign === 1 ? "extranjero" : "extranjeros"}` : ""].filter(Boolean).join(", ");
    const groups = [];
    list.forEach((r) => {
      let g = groups.find((x) => x.name === (r.pos_group || "Otros"));
      if (!g) { g = { name: r.pos_group || "Otros", order: r.pos_order == null ? 9 : r.pos_order, items: [] }; groups.push(g); }
      g.items.push(r);
    });
    groups.sort((a, b) => a.order - b.order);
    if (!groups.some((g) => g.name === squadGroup)) squadGroup = groups.length ? groups[0].name : null;
    const stOf = (r) => (playerComp === "all" ? { ...ZERO_STATS, ...(r.stats || {}) } : { ...ZERO_STATS, ...((r.comps || {})[playerComp] || {}) });
    const scope = playerComp === "all" ? "todas las competencias" : compLabel(playerComp);
    const cur = groups.find((g) => g.name === squadGroup);
    const grid = el("ul", { class: "pcards" });
    const show = () => grid.replaceChildren(...(cur ? cur.items.map((r) => playerCard(r, stOf(r))) : []));
    show();
    return el("div", { class: "squad" },
      el("p", { class: "meta", text: `${facts.charAt(0).toUpperCase()}${facts.slice(1)}. Estadísticas de ${scope}.` }),
      el("div", { class: "seg pos-tabs", role: "tablist", "aria-label": "Posición" },
        ...groups.map((g) => el("button", { type: "button", role: "tab", "aria-selected": g.name === squadGroup ? "true" : "false", text: `${g.name === "Mediocampistas" ? "Medios" : g.name} ${g.items.length}`,
          onclick: () => { squadGroup = g.name; renderPlayers(); } }))),
      grid);
  }

  function renderPlayers() {
    const box = $("players");
    box.replaceChildren();
    const roster = data.roster && data.roster.players && data.roster.players.length ? data.roster : null;
    const all = (data.players && data.players.players) || [];
    if (roster && all.length) {
      box.append(el("div", { class: "seg players-view", role: "group", "aria-label": "Vista de jugadores" },
        ...[["squad", "Plantel"], ["stats", "Estadísticas"]].map(([key, label]) => el("button", { type: "button", "aria-pressed": playersView === key ? "true" : "false", text: label,
          onclick: () => { playersView = key; renderPlayers(); } }))));
    }
    const showSquad = roster && (playersView === "squad" || !all.length);
    if (!all.length && !roster) {
      box.append(el("p", { class: "empty", text: "Aparecerán cuando haya alineaciones de partidos jugados." }));
      return;
    }
    // Competencias que aparecen en los datos: la liga primero.
    const found = [...new Set(all.flatMap((p) => Object.keys(p.comps || {})))];
    found.sort((a, b) => (a === LEAGUE() ? -1 : b === LEAGUE() ? 1 : a.localeCompare(b, "es")));
    if (playerComp !== "all" && !found.includes(playerComp)) playerComp = "all";
    const zero = { pj: 0, starts: 0, goals: 0, assists: 0, yellow: 0, red: 0 };
    const statsOf = (p) => (playerComp === "all" ? p : { ...p, ...zero, ...((p.comps || {})[playerComp] || {}) });
    const list = all.map(statsOf)
      .filter((p) => p.pj || p.goals || p.assists || p.yellow || p.red)
      .sort((a, b) => b.goals - a.goals || b.assists - a.assists || b.pj - a.pj || a.name.localeCompare(b.name, "es"));

    if (found.length > 1) {
      const opts = [["all", "Todas"], ...found.map((c) => [c, compLabel(c)])];
      box.append(el("div", { class: "seg players-seg", role: "group", "aria-label": "Competencia" },
        ...opts.map(([key, label]) => el("button", { type: "button", "aria-pressed": playerComp === key ? "true" : "false", text: label,
          onclick: () => { playerComp = key; showAllPlayers = false; renderPlayers(); } }))));
    }
    if (showSquad) { box.append(squadView(roster)); return; }
    const shown = showAllPlayers ? list : list.slice(0, 10);
    const v = (x) => (x ? x : "-");
    const head = el("tr", null,
      el("th", { scope: "col", text: "Jugador" }),
      el("th", { scope: "col", text: "PJ", title: "Partidos jugados" }),
      el("th", { scope: "col", text: "G", title: "Goles" }),
      el("th", { scope: "col", text: "A", title: "Asistencias" }),
      el("th", { scope: "col", class: "opt", text: "TA", title: "Tarjetas amarillas" }),
      el("th", { scope: "col", class: "opt", text: "TR", title: "Tarjetas rojas" }));
    const rows = shown.map((p) => el("tr", null,
      el("td", null, el("span", { class: "pcell" },
        el("span", { class: "jersey", text: p.jersey || "" }),
        el("span", { class: "pname", text: p.name }),
        p.pos ? el("span", { class: "ppos", text: p.pos }) : null)),
      el("td", { text: p.pj }),
      el("td", { class: p.goals ? "pts" : null, text: v(p.goals) }),
      el("td", { text: v(p.assists) }),
      el("td", { class: "opt", text: v(p.yellow) }),
      el("td", { class: "opt", text: v(p.red) })));
    const scope = playerComp === "all" ? "todas las competencias" : compLabel(playerComp);
    box.append(
      el("div", { class: "tablewrap" }, el("table", { class: "std players" },
        el("caption", { text: `${scope}, con los partidos que tienen alineación` }),
        el("thead", null, head), el("tbody", null, rows.length ? rows : el("tr", null, el("td", { colspan: "6", class: "empty", text: "Todavía no hay datos en esta competencia." }))))));
    if (list.length > 10) {
      const b = el("button", { class: "btn btn-ghost", type: "button", text: showAllPlayers ? "Ver menos" : `Ver los ${list.length} jugadores` });
      b.addEventListener("click", () => { showAllPlayers = !showAllPlayers; renderPlayers(); });
      box.append(b);
    }
  }

  // ---------- filtros, rendimiento y calendario completo ----------
  const LEAGUE = () => config.league_competition || "Liga Nacional de Guatemala";
  const allMatches = () => (data.matches && data.matches.matches) || [];
  const dayLong = (iso) => fDayLong(new Date(iso)).replace(",", "");
  const timeOf = (iso) => fTime(new Date(iso));
  const num = (n, d) => (n == null ? "-" : n.toFixed(d));
  let perfComp = "all";
  const cal = { comp: "all", when: "upcoming", venue: "all" };
  let pendingFocus = null;

  function competitions() {
    const seen = new Map();
    allMatches().forEach((m) => { if (m.competition) seen.set(m.competition, (seen.get(m.competition) || 0) + 1); });
    return [...seen.entries()].sort((a, b) => b[1] - a[1]).map(([k]) => k);
  }
  function filterBar(group, options, current, onPick) {
    return el("div", { class: "row", role: "group", "aria-label": group },
      el("span", { class: "lbl", text: group }),
      el("div", { class: "seg" }, ...options.map((o) => {
        const b = el("button", { type: "button", "aria-pressed": String(o.key === current), "data-g": group, "data-k": o.key, text: o.label });
        b.addEventListener("click", () => { pendingFocus = { g: group, k: o.key }; onPick(o.key); });
        return b;
      })));
  }
  function restoreFocus() {
    if (!pendingFocus) return;
    const b = document.querySelector(`button[data-g="${pendingFocus.g}"][data-k="${CSS.escape(pendingFocus.k)}"]`);
    pendingFocus = null;
    if (b) b.focus();
  }
  function myStanding() {
    for (const g of (data.standings && data.standings.groups) || []) {
      const r = g.rows.find((x) => x.is_municipal);
      if (r) return { pos: r.pos, pts: r.pts, pj: r.pj, league: compLabel(LEAGUE()) };
    }
    return null;
  }

  function renderPerformance() {
    const box = $("perf");
    box.replaceChildren();
    const S = window.MuniStats;
    if (!S) return;
    const all = S.played(allMatches(), config.team_id, config.team);
    if (!all.length) {
      box.append(el("p", { class: "empty", text: "Todavía no hay partidos jugados para calcular estadísticas." }));
      return;
    }
    const comps = competitions();
    if (perfComp !== "all" && !comps.includes(perfComp)) perfComp = "all";
    const list = perfComp === "all" ? all : all.filter((x) => x.competition === perfComp);
    const stats = S.summarize(list);
    const next = S.nextMatches(allMatches().filter((m) => perfComp === "all" || m.competition === perfComp),
      Date.now(), config.team_id, config.team, 5);
    const standing = perfComp === "all" || perfComp === LEAGUE() ? myStanding() : null;
    const sentences = S.narrative({
      team: config.team, scope: { all: perfComp === "all", label: perfComp === "all" ? "" : compLabel(perfComp) },
      stats, standing, next, fmt: { day: dayLong, time: timeOf },
    });

    if (comps.length > 1) {
      box.append(filterBar("Competencia", [{ key: "all", label: "Todas" }, ...comps.map((c) => ({ key: c, label: compLabel(c) }))],
        perfComp, (k) => { perfComp = k; renderPerformance(); }));
    }
    box.append(el("p", { class: "resumen", text: sentences.join(" ") }));
    if (!stats.pj) return;

    const items = [
      ["Partidos jugados", String(stats.pj), `${stats.g} G, ${stats.e} E, ${stats.p} P`],
      ["Partidos ganados", `${Math.round(stats.winPct)}%`, `${stats.g} de ${stats.pj}`],
      ["Puntos por partido", num(stats.ppg, 2), `${stats.pts} puntos`],
      ["Goles a favor por partido", num(stats.gfpg, 1), `${stats.gf} en total`],
      ["Goles en contra por partido", num(stats.gcpg, 1), `${stats.gc} en total`],
      ["Porterías en cero", String(stats.cleanSheets), `de ${stats.pj} partidos`],
    ];
    box.append(el("dl", { class: "statgrid" }, ...items.map(([k, v, note]) =>
      el("div", null, el("dt", { text: k }), el("dd", null, v, el("small", { text: note }))))));

    const row = (label, b) => el("tr", null, el("td", { text: label }),
      ...[b.pj, b.g, b.e, b.p, b.gf, b.gc].map((x) => el("td", { text: x })));
    box.append(el("h3", { text: "Local y visitante" }),
      el("div", { class: "tablewrap" }, el("table", { class: "std split" },
        el("thead", null, el("tr", null, el("th", { scope: "col", text: "" }),
          ...[["PJ", "Partidos jugados"], ["G", "Ganados"], ["E", "Empatados"], ["P", "Perdidos"], ["GF", "Goles a favor"], ["GC", "Goles en contra"]]
            .map(([t, title]) => el("th", { scope: "col", text: t, title })))),
        el("tbody", null, row("Local", stats.home), row("Visitante", stats.away)))));

    const rec = S.records(list);
    if (rec) {
      const game = (x) => x ? el("a", { href: `#/partido/${x.id}`, text: `${x.home ? "Municipal" : x.vs} ${x.home ? `${x.gf}-${x.gc} ${x.vs}` : `${x.gc}-${x.gf} Municipal`}` }) : "-";
      const row2 = (k, v) => el("li", null, el("span", { class: "rk", text: k }), el("span", { class: "rv" }, v));
      const seq = (n, one, many) => (n ? `${n} ${n === 1 ? one : many}` : "-");
      box.append(el("h3", { text: "Rachas y récords" }),
        el("ul", { class: "records" },
          row2("Mayor victoria", game(rec.bestWin)),
          row2("Peor derrota", game(rec.worstLoss)),
          row2("Partido con más goles", game(rec.mostGoals)),
          row2("Racha actual", stats.streak.win ? seq(stats.streak.win, "victoria seguida", "victorias seguidas")
            : stats.streak.unbeaten ? seq(stats.streak.unbeaten, "partido sin perder", "partidos sin perder") : seq(stats.streak.loss, "derrota seguida", "derrotas seguidas")),
          row2("Más victorias seguidas", seq(rec.longestWin, "victoria", "victorias")),
          row2("Más partidos sin perder", seq(rec.longestUnbeaten, "partido", "partidos")),
          row2("Más derrotas seguidas", seq(rec.longestLoss, "derrota", "derrotas"))));
    }

    box.append(el("h3", { text: "Resultados de la temporada" }),
      el("div", { class: "chips" }, ...list.map((x) =>
        el("span", { class: `chip ${x.res}`, text: x.res,
          title: `${x.home ? "Local" : "Visitante"} contra ${x.vs}: ${x.gf}-${x.gc}` }))));
    restoreFocus();
  }

  const isPlayed = (m) => m.state === "post" && !m.postponed;
  const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);

  function renderCalendarView() {
    const view = $("vista-calendario");
    view.replaceChildren(el("a", { class: "back", href: "#partidos", text: "Volver a partidos" }));
    const body = el("div", { class: "mv-body" });
    view.append(body, el("span"));
    body.append(el("h2", { class: "cal-title", text: "Todos los partidos" }));
    const ms = allMatches();
    if (!ms.length) {
      body.append(el("p", { class: "empty", text: "Todavía no hay partidos para mostrar." }));
      return;
    }
    const comps = competitions();
    if (cal.comp !== "all" && !comps.includes(cal.comp)) cal.comp = "all";
    const redo = () => renderCalendarView();
    const filters = el("div", { class: "filters" });
    if (comps.length > 1) {
      filters.append(filterBar("Competencia", [{ key: "all", label: "Todas" }, ...comps.map((c) => ({ key: c, label: compLabel(c) }))],
        cal.comp, (k) => { cal.comp = k; redo(); }));
    }
    filters.append(
      filterBar("Partidos", [{ key: "upcoming", label: "Próximos" }, { key: "played", label: "Jugados" }, { key: "all", label: "Todos" }],
        cal.when, (k) => { cal.when = k; redo(); }),
      filterBar("Sede", [{ key: "all", label: "Todas" }, { key: "home", label: "Local" }, { key: "away", label: "Visitante" }],
        cal.venue, (k) => { cal.venue = k; redo(); }));
    body.append(filters);

    let list = ms.filter((m) =>
      (cal.comp === "all" || m.competition === cal.comp) &&
      (cal.when === "all" || (cal.when === "played") === isPlayed(m)) &&
      (cal.venue === "all" || (cal.venue === "home") === isMe(m.home)));
    list.sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0));
    if (cal.when === "played") list.reverse();
    body.append(el("p", { class: "cal-count", text: `${list.length} ${list.length === 1 ? "partido" : "partidos"}` }));
    if (!list.length) {
      body.append(el("p", { class: "empty", text: "No hay partidos con esos filtros. Prueba con otra competencia o con Todos." }));
    }
    const monthOf = (m) => cap(fmt({ month: "long", year: "numeric" }).format(new Date(m.start)));
    let ol = null, last = "";
    list.forEach((m) => {
      const key = monthOf(m);
      if (key !== last) {
        last = key;
        body.append(el("h3", { class: "month", text: key }));
        ol = el("ol", { class: "matches" });
        body.append(ol);
      }
      ol.append(matchRow(m));
    });
    restoreFocus();
  }

  // ---------- página del partido ----------
  const KIND = { goal: "Gol", own_goal: "Autogol", yellow: "Amarilla", red: "Roja", sub: "Cambio" };

  function section(title, ...kids) {
    return el("section", { class: "mv-sec" }, el("h2", { text: title }), ...kids);
  }

  function rivalBlock(r, compact) {
    const bits = [];
    if (r.pos) bits.push(`${r.pos}.º en la tabla`);
    if (r.pts != null) bits.push(`${r.pts} puntos${r.pj ? ` en ${r.pj} partidos` : ""}`);
    // compact: la previa ("Cómo llegan") ya muestra al rival, su posición y sus últimos partidos
    return section(compact ? "Historial" : "El rival",
      compact ? null : el("div", { class: "rival" }, badge({ logo: r.logo, name: r.name }),
        el("div", null, el("strong", { text: r.name }), bits.length ? el("div", { class: "meta", text: bits.join(", ") }) : null)),
      !compact && r.form && r.form.length ? el("p", { class: "form" }, el("span", { text: "Sus últimos partidos:" }),
        ...r.form.map((f) => el("span", { class: `chip ${f.result}`, title: `${f.home ? "Local" : "Visitante"} contra ${f.vs}, ${f.score}`, text: f.result }))) : null,
      r.h2h && r.h2h.record ? el("div", { class: "h2h" }, el("h3", { text: "Historial entre ambos" }),
        el("p", { class: "h2h-rec" },
          el("span", null, el("strong", { text: r.h2h.record.g }), " ganó Municipal"),
          el("span", null, el("strong", { text: r.h2h.record.e }), " empates"),
          el("span", null, el("strong", { text: r.h2h.record.p }), ` ganó ${r.name}`)),
        el("p", { class: "meta", text: `En ${r.h2h.record.total} partidos que registra ESPN.` }),
        el("ul", { class: "plain" }, ...(r.h2h.last || []).map((x) => el("li", null,
          el("span", { text: `${x.home} ${x.score} ${x.away}` }),
          el("span", { class: "meta", text: [x.start && !isNaN(Date.parse(x.start)) ? `, ${fDay(new Date(x.start))}` : "", x.competition ? `, ${x.competition}` : ""].join("") }))))) : null,
      r.meetings && r.meetings.length ? el("div", null, el("h3", { text: "Se enfrentaron esta temporada" }),
        el("ul", { class: "plain" }, ...r.meetings.map((x) => el("li", null,
          el("a", { href: `#/partido/${x.id}`, text: `${x.home} ${x.score} ${x.away}` }),
          el("span", { class: "meta", text: `, ${fDay(new Date(x.start))}` }))))) : null,
      el("p", { class: "meta" }, el("a", { href: "https://www.fotmob.com/teams/9933/overview/csd-municipal", target: "_blank", rel: "noopener noreferrer", text: "Ver más estadísticas de Municipal en FotMob" })));
  }

  function timelineList(m, items) {
    const homeId = m.home.id;
    return el("ol", { class: "tl" }, ...items.map((e) => {
      const label = e.kind === "goal" && e.penalty ? "Gol de penal" : KIND[e.kind];
      const who = e.kind === "sub" ? e.text : e.player;
      const body = el("div", { class: `ev-body k-${e.kind}` },
        el("span", { class: "ev-kind", text: label }),
        who ? el("span", { class: "ev-who", text: who }) : null,
        e.assist ? el("span", { class: "meta", text: `Asistencia: ${e.assist}` }) : null);
      const home = e.team_id === homeId;
      return el("li", { class: "ev" },
        el("div", { class: "ev-side home" }, home ? body : null),
        el("span", { class: "ev-min", text: e.min }),
        el("div", { class: "ev-side away" }, home ? null : body));
    }));
  }

  function timeline(m, events) {
    const items = events.filter((e) => KIND[e.kind]);
    if (!items.length) return null;
    return section("Cronología", timelineList(m, items));
  }

  function ofCredit(of) {
    return el("p", { class: "meta of-credit" }, "Datos de ",
      el("a", { href: safeUrl(of.url), target: "_blank", rel: "noopener noreferrer", text: "OneFootball" }), ".");
  }

  /** Eventos de OneFootball: solo suman. Si ESPN no trae cronología la reemplaza (con su fuente a la vista);
   *  si trae menos eventos, deja los de ESPN como están y agrega la lista completa aparte. */
  function ofEventsBlock(m, of, espnEvents) {
    const items = ((of && of.events) || []).filter((e) => KIND[e.kind]);
    if (!items.length) return null;
    const have = (espnEvents || []).filter((e) => KIND[e.kind]).length;
    if (!have) return section("Cronología", timelineList(m, items), ofCredit(of));
    if (items.length <= have) return null;
    return section("Todos los eventos", el("details", null,
      el("summary", { text: `Ver los ${items.length} eventos (ESPN muestra ${have})` }),
      timelineList(m, items), ofCredit(of)));
  }

  /** Minuto a minuto de ESPN, plegado: complementa la cronología sin cambiarla. */
  function commentaryBlock(m, items) {
    if (!items || !items.length) return null;
    const list = items.slice().reverse(); // lo más reciente arriba
    return section("Minuto a minuto", el("details", null,
      el("summary", { text: `Ver las jugadas (${items.length})` }),
      el("ol", { class: "comm" }, ...list.map((c) => el("li", { class: c.team_id === m.home.id ? "h" : c.team_id === m.away.id ? "a" : "" },
        el("span", { class: "ev-min", text: c.min }), el("span", { class: "ctext", text: c.text }))))));
  }

  function statsBlock(m, stats) {
    if (!stats.length) return null;
    const meHome = isMe(m.home);
    return section("Estadísticas", el("div", { class: "stats" },
      el("div", { class: "stat-head" }, el("span", { text: m.home.name }), el("span", { text: m.away.name })),
      ...stats.map((s) => {
        const total = (s.home_v || 0) + (s.away_v || 0);
        const hp = total ? (s.home_v / total) * 100 : 50;
        return el("div", { class: "stat" },
          el("span", { class: "sv", text: s.home }),
          el("div", { class: "sbar-wrap" },
            el("span", { class: "sl", text: s.label }),
            el("div", { class: "sbar", role: "img", "aria-label": `${s.label}: ${s.home} contra ${s.away}` },
              el("span", { class: meHome ? "sb-me" : "sb-other", style: `width:${hp}%` }),
              el("span", { class: meHome ? "sb-other" : "sb-me", style: `width:${100 - hp}%` }))),
          el("span", { class: "sv", text: s.away }));
      })));
  }

  const MARK_TEXT = { yellow: "Tarjeta amarilla", red: "Tarjeta roja", goal: "Gol", out: "Salió", in: "Entró", captain: "Capitán" };
  function markIcons(marks, cls) {
    if (!marks || !marks.length) return null;
    return el("span", { class: cls, "aria-label": marks.map((k) => MARK_TEXT[k] || k).join(", ") },
      ...marks.map((k) => el("i", { class: `mk mk-${k}`, title: MARK_TEXT[k] || k, "aria-hidden": "true",
        text: k === "goal" ? "⚽" : k === "out" ? "▼" : k === "in" ? "▲" : k === "captain" ? "C" : "" })));
  }

  function pitchView(lu, mine) {
    const P = window.MuniPitch;
    const rows = P && P.layout(lu.formation, lu.players);
    if (!rows) return null;
    const n = rows.length;
    const pitch = el("div", { class: `pitch${mine ? " me" : ""}`, role: "group",
      "aria-label": `Alineación de ${lu.team}, formación ${lu.formation}` },
      el("span", { class: "pl-box box-t" }), el("span", { class: "pl-box box-b" }), el("span", { class: "pl-mid" }));
    rows.forEach((row, ri) => {
      const bottom = 8 + ri * (84 / (n - 1));
      row.forEach((p, ci) => {
        const dot = el("div", { class: "pl", style: `left:${((ci + 0.5) / row.length) * 100}%;bottom:${bottom}%` },
          el("span", { class: "pl-dot", text: p.jersey || "" }),
          el("span", { class: "pl-name", text: P.shortName(p.name) }),
          markIcons(p.marks, "pl-marks"));
        pitch.append(dot);
      });
    });
    return pitch;
  }

  function lineupsBlock(m, lineups, of) {
    if (!lineups.length) return null;
    const ordered = [...lineups].sort((a, b) => (a.team_id === m.home.id ? -1 : 1) - (b.team_id === m.home.id ? -1 : 1));
    return section("Alineaciones", el("div", { class: "lineups" }, ...ordered.map((lu0) => {
      // Sin formación en la fuente: para Municipal se estima con las posiciones del plantel de ESPN.
      let lu = lu0, estimated = false;
      if (!lu0.formation && window.MuniFormation && isMe({ id: lu0.team_id, name: lu0.team }) && data.roster && data.roster.players) {
        const est = window.MuniFormation.estimate(lu0.players, data.roster.players);
        if (est) { lu = { ...lu0, formation: est.formation, players: est.players }; estimated = true; }
      }
      const li = (p) => el("li", null, el("span", { class: "jersey", text: p.jersey || "" }), el("span", { class: "pname", text: p.name }), markIcons(p.marks, "li-marks"), p.pos ? el("span", { class: "ppos", text: p.pos }) : null);
      const bench = lu.players.filter((p) => !p.starter);
      const pitch = pitchView(lu, isMe({ id: lu.team_id, name: lu.team }));
      const starters = el("ul", { class: "plain" }, ...lu.players.filter((p) => p.starter).map(li));
      return el("div", { class: "lu" },
        el("h3", { text: lu.team + (lu.formation ? ` (${lu.formation}${estimated ? ", estimada" : ""})` : "") }),
        pitch,
        pitch && estimated ? el("p", { class: "meta", text: "Formación estimada con las posiciones del plantel; la real puede variar." }) : null,
        pitch ? el("details", null, el("summary", { text: "Ver la lista de titulares" }), starters) : starters,
        bench.length ? (lu.manual ? el("div", null, el("h4", { text: "Banquillo" }), el("ul", { class: "plain" }, ...bench.map(li)))
          : el("details", null, el("summary", { text: `Suplentes (${bench.length})` }), el("ul", { class: "plain" }, ...bench.map(li)))) : null,
        lu.coach ? el("p", { class: "meta", text: `Entrenador: ${lu.coach}` }) : null,
        lu.manual && lu.source ? el("p", { class: "meta", text: `Alineación cargada a mano. Fuente: ${lu.source}.` }) : null);
    })), of ? ofCredit(of) : null);
  }

  async function renderMatchView(id) {
    const view = $("vista-partido");
    const m = ((data.matches && data.matches.matches) || []).find((x) => x.id === id);
    view.replaceChildren(el("a", { class: "back", href: "#partidos", text: "Volver a partidos" }));
    if (!m) {
      view.append(el("p", { class: "empty pad", text: "No encontramos ese partido. Puede que ya no esté en el calendario." }));
      return;
    }
    document.title = `${m.home.name} ${m.state === "pre" ? "vs" : `${m.home.score ?? "-"}-${m.away.score ?? "-"}`} ${m.away.name} | ${BASE_TITLE}`;
    const head = el("section", { class: "board" }, el("div", { class: "board-inner" }));
    fillBoard(head.firstChild, m);
    view.append(head);
    const body = el("div", { class: "mv-body" });
    view.append(body);

    let detail = null;
    try { detail = await getJson(`match/${id}`); } catch (_) { detail = null; }
    if (!location.hash.startsWith(`#/partido/${id}`)) return; // el usuario ya se fue
    const prev = previaBlock(m, detail && detail.rival);
    const parts = detail ? [
      m.state === "pre" && detail.rival ? rivalBlock(detail.rival, !!prev) : null,
      timeline(m, detail.events || []),
      ofEventsBlock(m, detail.of, detail.events),
      commentaryBlock(m, detail.commentary),
      statsBlock(m, detail.stats || []),
      (detail.lineups || []).length ? lineupsBlock(m, detail.lineups) : lineupsBlock(m, (detail.of && detail.of.lineups) || [], detail.of),
    ].filter(Boolean) : [];
    if (prev) parts.unshift(prev);
    else { const fcard = forecastCard(m); if (fcard) parts.unshift(fcard); }
    if (parts.length) body.append(...parts);
    else body.append(el("p", { class: "empty", text: m.state === "pre" ? "Las alineaciones y estadísticas aparecen cuando empieza el partido." : "ESPN todavía no publica el detalle de este partido." }));
    const share = el("button", { class: "btn btn-ghost", type: "button", text: "Compartir este partido" });
    share.addEventListener("click", async () => {
      const url = location.href, title = document.title;
      try {
        if (navigator.share) await navigator.share({ title, url });
        else { await navigator.clipboard.writeText(url); share.textContent = "Enlace copiado"; }
      } catch (_) { /* el usuario canceló */ }
    });
    const img = el("button", { class: "btn btn-ghost", type: "button", text: "Compartir imagen" });
    img.addEventListener("click", async () => {
      if (!window.MuniCard) return;
      img.disabled = true;
      try {
        const model = window.MuniCard.cardModel(m, (detail && detail.events) || (detail && detail.of && detail.of.events) || [], {
          competition: compLabel(m.competition), when: m.start ? `${dayLong(m.start)}, ${timeOf(m.start)}` : "", footer: "Municipal en vivo" });
        const blob = await window.MuniCard.makeBlob(model);
        if (!blob) throw new Error("sin imagen");
        const file = new File([blob], "municipal.png", { type: "image/png" });
        if (navigator.canShare && navigator.canShare({ files: [file] })) await navigator.share({ files: [file], title: document.title });
        else { const a = el("a", { href: URL.createObjectURL(blob), download: "municipal.png" }); document.body.append(a); a.click(); a.remove(); }
      } catch (e) { if (!e || e.name !== "AbortError") img.textContent = "No se pudo crear la imagen"; }
      img.disabled = false;
    });
    body.append(el("p", { class: "actions" },
      el("a", { class: "btn", href: safeUrl(m.url), target: "_blank", rel: "noopener", text: "Ver este partido en ESPN" }), share, img,
      window.MuniShare ? waButton(window.MuniShare.matchText(m, { competition: compLabel(m.competition), url: location.href,
        when: m.start ? `${dayLong(m.start)}, ${timeOf(m.start)}` : "" })) : null));
  }

  function route() {
    const matchHit = location.hash.match(/^#\/partido\/(\d+)/);
    const calHit = /^#\/calendario/.test(location.hash);
    const home = $("home"), mv = $("vista-partido"), cv = $("vista-calendario");
    if (!matchHit && !calHit) {
      const wasView = !mv.hidden || !cv.hidden;
      mv.hidden = true; cv.hidden = true; home.hidden = false;
      document.title = BASE_TITLE;
      const target = location.hash.length > 1 ? document.getElementById(decodeURIComponent(location.hash.slice(1))) : null;
      if (wasView) { if (target) target.scrollIntoView(); else window.scrollTo(0, 0); }
      return;
    }
    const wasHome = !home.hidden;
    home.hidden = true;
    mv.hidden = !matchHit; cv.hidden = !calHit;
    if (wasHome) window.scrollTo(0, 0);
    if (matchHit) renderMatchView(matchHit[1]);
    else { document.title = `Todos los partidos | ${BASE_TITLE}`; renderCalendarView(); }
  }

  // ---------- noticias ----------
  let newsShown = 12;
  let newsTopic = "all";
  function renderNews() {
    const list = $("news-list"), more = $("news-more");
    list.replaceChildren();
    more.replaceChildren();
    const all = (data.news && data.news[newsFeed]) || [];
    const T = window.MuniTopics;
    const topicsBox = $("news-topics");
    topicsBox.replaceChildren();
    if (T && all.length) {
      const counts = T.counts(all);
      if (newsTopic !== "all" && !counts[newsTopic]) newsTopic = "all";
      if (T.TOPICS.some((t) => counts[t.key])) {
        topicsBox.append(filterBar("Tema", [{ key: "all", label: "Todas" },
          ...T.TOPICS.filter((t) => counts[t.key]).map((t) => ({ key: t.key, label: `${t.label} (${counts[t.key]})` }))],
          newsTopic, (k) => { newsTopic = k; newsShown = 12; renderNews(); restoreFocus(); }));
      }
    }
    const items = T ? T.filter(all, newsTopic) : all;
    if (!items.length) {
      list.append(el("li", { class: "empty", text: "No hay noticias por ahora." }));
      return;
    }
    items.slice(0, newsShown).forEach((n) => list.append(el("li", null,
      el("a", { href: safeUrl(n.url), target: "_blank", rel: "noopener" },
        el("div", null,
          el("div", { class: "hl", text: n.title }),
          n.summary ? el("p", { class: "sum", text: n.summary }) : null,
          el("div", { class: "src", text: [n.source, n.published ? ago(n.published) : ""].filter(Boolean).join(", ") })),
        n.image && /^https?:/.test(n.image) ? el("img", { src: n.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" }) : el("span")))));
    const srcs = (newsFeed === "municipal" && data.news.sources) || [];
    more.append(el("p", { class: "meta", text: `${items.length} noticias${srcs.length ? ` de ${srcs.length} medios` : ""}. Se guardan las de los últimos meses.` }));
    if (items.length > newsShown) {
      const b = el("button", { class: "btn btn-ghost", type: "button", text: `Ver más (${items.length - newsShown})` });
      b.addEventListener("click", () => { newsShown += 12; renderNews(); });
      more.append(b);
    }
  }
  const feedTabs = document.querySelectorAll('.seg[role="tablist"] button');
  feedTabs.forEach((b) => b.addEventListener("click", () => {
    newsFeed = b.dataset.feed;
    newsShown = 12;
    newsTopic = "all";
    feedTabs.forEach((x) => {
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
    const ig = config.instagram_handle;
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
      p.textContent = `Actualizado ${ago(meta.updated)}, con datos de ESPN, buscadores de noticias y medios guatemaltecos.` +
        (data.liveAt ? ` Tabla y marcadores al día con ESPN ${ago(data.liveAt)}.` : "") +
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
  const LIVE_SLUGS = ["gua.1", "concacaf.central.american.cup", "concacaf.champions"];
  async function fetchLive(url, ms = 8000) {
    const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), ms);
    try {
      const r = await fetch(url, { signal: ctl.signal, cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } finally { clearTimeout(t); }
  }
  /** Pone la tabla y los marcadores al día con ESPN. Si falla, no pasa nada: quedan los datos publicados. */
  async function liveRefresh() {
    const LV = window.MuniLive;
    if (!LV) return false;
    const [st, ...boards] = await Promise.allSettled([fetchLive(LV.standingsUrl("gua.1")),
      ...LIVE_SLUGS.map((s) => fetchLive(LV.scoreboardUrl(s, Date.now())))]);
    let changed = false;
    if (st.status === "fulfilled") {
      try {
        const groups = LV.chooseStandings(LV.parseStandings(st.value, config.team_id, config.team), data.standings);
        if (groups) { data.standings = { groups, stale: false, live: true }; changed = true; }
      } catch (_) { /* formato inesperado: se ignora */ }
    }
    const board = {};
    boards.forEach((b) => { if (b.status === "fulfilled") { try { Object.assign(board, LV.parseScoreboard(b.value)); } catch (_) { /* ignorar */ } } });
    if (data.matches && Object.keys(board).length) {
      const r = LV.mergeMatches(data.matches.matches, board, config.team_id, config.team);
      if (r.changed) { data.matches = { ...data.matches, matches: r.matches }; changed = true; }
    }
    data.liveAt = changed || data.liveAt ? new Date().toISOString() : null;
    return changed;
  }
  function renderAll() {
    if (data.matches) { renderBoard(); renderMatches(); }
    renderStandings(); renderLiguilla(); renderPerformance(); renderPlayers(); renderNews(); renderFooter();
  }
  let loaded = false;
  async function load() {
    const names = ["matches", "standings", "news", "meta", "players", "odds", "history", "roster"];
    const res = await Promise.allSettled(names.map(getJson));
    names.forEach((n, i) => { if (res[i].status === "fulfilled") data[n] = res[i].value; });
    if (res[0].status === "rejected" && !data.matches) {
      $("board").replaceChildren(el("p", { class: "board-msg", text: "No se pudieron cargar los partidos. Recarga la página en unos minutos." }));
    }
    if (loaded) await liveRefresh(); // ya hay datos en pantalla: se actualiza todo junto, sin parpadeo
    renderAll();
    schedule();
    if (!loaded) { loaded = true; if (await liveRefresh()) { renderAll(); if ($("home").hidden) route(); } }
  }
  function schedule() {
    clearTimeout(timer);
    const live = data.matches && data.matches.matches.some((m) => m.state === "in");
    timer = setTimeout(async () => { await load(); if ($("home").hidden) route(); }, live ? 45e3 : 180e3);
  }

  /** Barra de pestañas fija abajo (solo se ve en el celular): resalta la sección que se está viendo. */
  function setupTabbar() {
    const bar = document.querySelector(".tabbar");
    if (!bar) return;
    const btn = bar.querySelector(".tab-more"), menu = $("more-menu");
    const close = () => { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); };
    btn.addEventListener("click", () => { const open = menu.hidden; menu.hidden = !open; btn.setAttribute("aria-expanded", String(open)); });
    menu.addEventListener("click", (e) => { if (e.target.closest("a")) close(); });
    document.addEventListener("click", (e) => { if (!menu.hidden && !e.target.closest(".more-menu, .tab-more")) close(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
    window.addEventListener("hashchange", close);
    const tabOf = { marcador: "marcador", partidos: "partidos", tabla: "tabla", liguilla: "liguilla" };
    const ids = ["marcador", "liguilla", "partidos", "noticias", "tabla", "rendimiento", "jugadores", "redes"];
    let pending = false;
    const mark = () => {
      pending = false;
      let tab = null;
      if (!$("home").hidden) {
        let best = -Infinity;
        for (const id of ids) {
          const top = $(id).getBoundingClientRect().top;
          if (top <= 140 && top > best) { best = top; tab = tabOf[id] || "more"; }
        }
        tab = tab || "marcador";
      }
      bar.querySelectorAll("[data-tab]").forEach((n) => {
        if (n.dataset.tab === tab) n.setAttribute("aria-current", "true"); else n.removeAttribute("aria-current");
      });
    };
    const queue = () => { if (!pending) { pending = true; requestAnimationFrame(mark); } };
    window.addEventListener("scroll", queue, { passive: true });
    window.addEventListener("hashchange", queue);
    window.addEventListener("resize", queue);
    mark();
  }

  async function init() {
    try { config = await (await fetch("config.json", { cache: "no-store" })).json(); } catch (_) { config = {}; }
    config.team = config.team || "Municipal";
    config.team_id = config.team_id || "7258";
    if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
      navigator.serviceWorker.register("sw.js").catch(() => { /* sin soporte: el sitio funciona igual */ });
    }
    renderSubscribe();
    renderSocial();
    await load();
    route();
    window.addEventListener("hashchange", route);
    setupTabbar();
    setInterval(tickCountdown, 30e3);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) load(); });
  }
  init();
})();
