const assert = require("assert");
const L = require("../site/live.js");

const entry = (id, name, pj, pts, gf, gc, rank) => ({ team: { id, displayName: name, logos: [{ href: `https://x/${id}.png` }] },
  stats: [["gamesPlayed", pj], ["points", pts], ["pointsFor", gf], ["pointsAgainst", gc], ["pointDifferential", gf - gc], ["rank", rank]]
    .map(([name, value]) => ({ name, value })), note: { description: "Clasifica" } });
const names = ["Comunicaciones", "Municipal", "Antigua", "Xelajú", "Cobán", "Malacateco", "Mixco", "Marquense", "Guastatoya", "Aurora"];
const raw = { children: [{ name: "", standings: { entries: names.map((n, i) => entry(String(i + 1), n, 14, 30 - i, 20 - i, 10 + i, i + 1)).reverse() } }] };

// tabla: orden por rank, Municipal marcado, campos numéricos
const g = L.parseStandings(raw, "2", "Municipal");
assert.strictEqual(g[0].rows[0].name, "Comunicaciones");
assert.strictEqual(g[0].rows[1].is_municipal, true);
assert.strictEqual(g[0].rows[1].pos, 2);
assert.strictEqual(g[0].rows[0].pts, 30);
assert.strictEqual(g[0].rows[0].logo, "https://x/1.png");
assert.strictEqual(g[0].rows[0].note, "Clasifica");
assert.deepStrictEqual(L.parseStandings({}, "2", "Municipal"), []);

// aceptar solo tablas completas y no atrasadas
assert.ok(L.chooseStandings(g, null));
assert.ok(L.chooseStandings(g, { groups: g }));
const older = JSON.parse(JSON.stringify(g)); older[0].rows[0].pj = 13;
assert.strictEqual(L.chooseStandings(older, { groups: g }), null);
const incomplete = JSON.parse(JSON.stringify(g)); incomplete[0].rows[3].pts = null;
assert.strictEqual(L.chooseStandings(incomplete, null), null);
assert.strictEqual(L.chooseStandings([{ rows: g[0].rows.slice(0, 5) }], null), null);

// marcadores
const ev = (id, home, away, hs, as, state, extra = {}) => ({ id, date: "2026-11-14T02:00Z",
  status: { displayClock: "67'", type: { state, completed: state === "post", name: extra.name || "STATUS", shortDetail: extra.detail || "FT" } },
  competitions: [{ competitors: [{ homeAway: "home", score: hs, team: { id: home } }, { homeAway: "away", score: as, team: { id: away } }] }] });
const board = L.parseScoreboard({ events: [ev("10", "2", "9", "2", "1", "post"), ev("11", "5", "2", "0", "0", "in"), ev("12", "2", "6", "", "", "pre", { name: "STATUS_POSTPONED" })] });
assert.strictEqual(board["10"].completed, true);
assert.strictEqual(board["10"].home.score, 2);
assert.strictEqual(board["12"].postponed, true);
assert.strictEqual(board["12"].home.score, null);

const mk = (id, h, a, state) => ({ id, start: "2026-11-01T00:00:00Z", state, completed: false, postponed: false, status: "", clock: "",
  home: { id: h, name: `T${h}`, score: null }, away: { id: a, name: `T${a}`, score: null } });
const r = L.mergeMatches([mk("10", "2", "9", "in"), mk("11", "5", "2", "pre"), mk("99", "1", "2", "pre")], board, "2", "Municipal");
assert.strictEqual(r.matches[0].state, "post");
assert.strictEqual(r.matches[0].result, "G");               // Municipal local 2-1
assert.strictEqual(r.matches[0].start, "2026-11-14T02:00:00Z"); // reprogramado por ESPN
assert.strictEqual(r.matches[1].state, "in");
assert.strictEqual(r.matches[1].result, null);
assert.strictEqual(r.matches[2].id, "99");                   // lo que ESPN no menciona queda igual
assert.strictEqual(r.matches[2].state, "pre");
assert.strictEqual(r.changed, 2);
assert.strictEqual(mk("10", "2", "9", "in").state, "in");   // no muta el original

// derrota como visitante
assert.strictEqual(L.resultFor({ state: "post", home: { id: "5", score: 3 }, away: { id: "2", score: 1 } }, "2", "Municipal"), "P");

// URLs
assert.ok(L.scoreboardUrl("gua.1", new Date("2026-11-07T09:00:00Z")).includes("dates=20261105-20261121"));
assert.ok(L.standingsUrl("gua.1").endsWith("/gua.1/standings"));
console.log("live.test.js: OK");
