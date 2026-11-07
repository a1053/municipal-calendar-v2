const assert = require("assert");
const S = require("../site/share.js");
const m = (state, hs, as, extra = {}) => ({ state, status: "", home: { name: "Municipal", score: hs }, away: { name: "Antigua", score: as }, ...extra });
const url = "https://x.test/#/partido/1";

assert.strictEqual(S.matchText(m("post", 2, 1), { competition: "Liga Bantrab", url }), `Final (Liga Bantrab): Municipal 2-1 Antigua\n${url}`);
assert.ok(S.matchText(m("in", 1, 1, { status: "65'" }), { url }).startsWith("EN VIVO: Municipal 1-1 Antigua (65')"));
const pre = S.matchText(m("pre", null, null, { broadcasts: ["Tigo Sports"] }), { when: "sáb 14 nov, 7:00 p. m.", url });
assert.ok(pre.startsWith("Próximo partido: Municipal vs Antigua, sáb 14 nov, 7:00 p. m.") && pre.includes("Dónde verlo: Tigo Sports"));
assert.ok(S.matchText(m("pre", null, null, { postponed: true }), { url }).startsWith("Partido aplazado"));
assert.ok(!S.matchText(m("post", 0, 0, { broadcasts: ["X"] }), { url }).includes("Dónde verlo"));

const rows = Array.from({ length: 12 }, (_, i) => ({ name: `E${i + 1}`, pts: 30 - i, pos: i + 1, is_municipal: i === 8 }));
const t = S.tableText(rows, { tournament: "Apertura 2026", url: "u" });
assert.ok(t.includes("1. E1 30 pts") && t.includes("6. E6 25 pts") && !t.includes("7. E7"));
assert.ok(t.includes("...\n9. E9 22 pts"));                      // Municipal fuera del top: se agrega aparte
assert.ok(!S.tableText(rows.map((r, i) => ({ ...r, is_municipal: i === 1 })), { url: "u" }).includes("..."));

const l = S.ligaText(["Municipal es 2.º con 28 puntos.", "a", "b", "c"], { p_qualify: 99.6, p_direct: 0.4 }, { tournament: "Apertura 2026", url: "u" });
assert.ok(l.includes("clasificar: >99%") && l.includes("directo a semifinales: <1%") && !l.includes("\nc\n"));
assert.ok(!S.ligaText([], null, { url: "u" }).includes("Probabilidad"));

assert.ok(S.matchText(m("pre", null, null), { when: "x".repeat(3000), url }).length <= 1500);
assert.strictEqual(S.whatsappUrl("a b&c"), "https://wa.me/?text=a%20b%26c");
console.log("share.test.js: OK");
