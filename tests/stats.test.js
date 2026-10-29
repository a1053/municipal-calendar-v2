// Pruebas de site/stats.js. Ejecutar: node tests/stats.test.js
const assert = require("assert");
const S = require("../site/stats.js");

const ME = { id: "7258", name: "Municipal" };
const side = (name, id, score) => ({ id, name, score });
function match(id, start, home, away, state = "post", extra = {}) {
  return { id, start, state, postponed: false, competition: "Liga", home, away, ...extra };
}
const M = (id, start, mine, theirs, atHome, comp) =>
  match(id, start, atHome ? side("Municipal", "7258", mine) : side("Rival", "9", theirs),
        atHome ? side("Rival", "9", theirs) : side("Municipal", "7258", mine), "post", { competition: comp || "Liga" });

const matches = [
  M("1", "2026-08-01T00:00:00Z", 2, 0, true),          // G local, valla en cero
  M("2", "2026-08-08T00:00:00Z", 1, 1, false),         // E visita
  M("3", "2026-08-15T00:00:00Z", 0, 2, true),          // P local, sin marcar
  M("4", "2026-08-22T00:00:00Z", 3, 1, false),         // G visita
  M("5", "2026-08-29T00:00:00Z", 1, 0, true, "Copa"),  // G local, otra competencia
  match("6", "2026-09-05T00:00:00Z", side("Municipal", "7258", null), side("X", "3", null), "pre"),
  match("7", "2026-09-06T00:00:00Z", side("Municipal", "7258", null), side("Y", "4", null), "post", { postponed: true }),
];

// played: ignora pendientes y aplazados, ordena y ve todo desde Municipal
const p = S.played(matches, "7258", "Municipal");
assert.deepStrictEqual(p.map((x) => x.res), ["G", "E", "P", "G", "G"]);
assert.strictEqual(p[1].home, false);
assert.strictEqual(p[1].gf, 1);
assert.strictEqual(S.played(matches.slice().reverse(), "7258", "Municipal")[0].id, "1");

// summarize
const s = S.summarize(p);
assert.strictEqual(s.pj, 5);
assert.deepStrictEqual([s.g, s.e, s.p], [3, 1, 1]);
assert.strictEqual(s.pts, 10);
assert.strictEqual(s.ppg, 2);
assert.strictEqual(s.winPct, 60);
assert.deepStrictEqual([s.gf, s.gc, s.dg], [7, 4, 3]);
assert.strictEqual(s.cleanSheets, 2);
assert.strictEqual(s.failedToScore, 1);
assert.deepStrictEqual([s.home.pj, s.home.g, s.home.gf, s.home.gc], [3, 2, 3, 2]);
assert.deepStrictEqual([s.away.pj, s.away.e, s.away.gf, s.away.gc], [2, 1, 4, 2]);
assert.deepStrictEqual(s.streak, { win: 2, unbeaten: 2, loss: 0 });
assert.strictEqual(s.last.length, 5);

// vacío
const z = S.summarize([]);
assert.strictEqual(z.pj, 0);
assert.strictEqual(z.ppg, null);
assert.strictEqual(z.winPct, null);

// nextMatches
const now = Date.parse("2026-09-01T00:00:00Z");
const nx = S.nextMatches(matches, now, "7258", "Municipal", 5);
assert.deepStrictEqual(nx.map((x) => [x.id, x.home, x.vs]), [["6", true, "X"]]);

// narrative
const fmt = { day: () => "sábado 5 de septiembre", time: () => "5:00 p. m." };
const text = S.narrative({
  team: "Municipal", scope: { all: false, label: "Liga Bantrab" }, stats: S.summarize(p.slice(0, 4)),
  standing: { pos: 1, pts: 28, pj: 14, league: "Liga Bantrab" }, next: nx, fmt,
}).join(" ");
assert.ok(text.startsWith("Municipal es 1.º de la Liga Bantrab con 28 puntos en 14 partidos."), text);
assert.ok(text.includes("En Liga Bantrab ha jugado 4 partidos: 2 ganados, 1 empatado y 1 perdido"), text);
assert.ok(text.includes("con 6 goles a favor y 4 en contra"), text);
assert.ok(text.includes("En sus últimos 4 partidos ganó 2, empató 1 y perdió 1."), text);
assert.ok(text.includes("Dejó su portería en cero en 1 de 4 partidos."), text);
assert.ok(text.includes("Su próximo partido es de local contra X, el sábado 5 de septiembre a las 5:00 p. m."), text);
assert.ok(!text.includes(".."), text);

// plural de próximos y rachas
const many = [{ home: true, vs: "A", start: "x" }, { home: false, vs: "B", start: "x" }, { home: true, vs: "C", start: "x" }];
const t2 = S.narrative({ team: "Municipal", scope: { all: true, label: "" }, stats: S.summarize([]), standing: null, next: many, fmt }).join(" ");
assert.ok(t2.startsWith("Todavía no ha jugado partidos."), t2);
assert.ok(t2.includes("De sus próximos 3 partidos, 2 son de local y 1 es de visitante. El siguiente es de local contra A"), t2);

const wins = [1, 2, 3, 4].map((i) => ({ res: "G", home: true, gf: 1, gc: 0 }));
const t3 = S.narrative({ team: "Municipal", scope: { all: true }, stats: S.summarize(wins), next: [], fmt }).join(" ");
assert.ok(t3.includes("Ganó sus últimos 4 partidos."), t3);
assert.ok(!t3.includes("sin perder"), t3);
const unb = [{ res: "E", home: true, gf: 1, gc: 1 }, { res: "G", home: true, gf: 1, gc: 0 }, { res: "E", home: true, gf: 0, gc: 0 }];
assert.ok(S.narrative({ team: "M", scope: { all: true }, stats: S.summarize(unb), next: [], fmt }).join(" ").includes("Lleva 3 partidos sin perder."));

console.log("stats.test.js: OK");
