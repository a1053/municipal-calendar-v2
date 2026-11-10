const assert = require("assert");
const P = require("../site/previa.js");
const rows = [
  { team_id: "7258", name: "Municipal", pos: 1, pts: 28, pj: 14, gf: 28, gc: 12, dg: 16 },
  { team_id: "9", name: "Comunicaciones", pos: 2, pts: 27, pj: 14, gf: 21, gc: 14, dg: 7 },
  { team_id: "5", name: "Sin datos", pos: 3, pts: null, pj: 0, gf: null, gc: null, dg: null },
];

const c = P.compare(rows, "7258", "9");
assert.deepStrictEqual(c.rows.map((r) => r.label), ["Posición", "Puntos", "Puntos por partido", "Goles a favor por partido", "Goles en contra por partido", "Diferencia de goles"]);
const by = Object.fromEntries(c.rows.map((r) => [r.label, r]));
assert.deepStrictEqual([by["Posición"].a, by["Posición"].b, by["Posición"].better], ["1.º", "2.º", "a"]);   // menos es mejor
assert.deepStrictEqual([by["Puntos"].a, by["Puntos"].b, by["Puntos"].better], ["28", "27", "a"]);
assert.deepStrictEqual([by["Goles a favor por partido"].a, by["Goles a favor por partido"].b], ["2.0", "1.5"]);
assert.deepStrictEqual([by["Goles en contra por partido"].a, by["Goles en contra por partido"].b, by["Goles en contra por partido"].better], ["0.9", "1.0", "a"]);
assert.strictEqual(by["Diferencia de goles"].a, "+16");

// quien está del lado b también puede ser el mejor
const inv = P.compare(rows, "9", "7258");
assert.strictEqual(inv.rows[0].better, "b");

// empate en un dato: nadie se marca mejor
const tied = P.compare([{ ...rows[0] }, { ...rows[1], pts: 28 }], "7258", "9");
assert.strictEqual(tied.rows.find((r) => r.label === "Puntos").better, null);

// datos que faltan
assert.strictEqual(P.compare(rows, "7258", "5"), null);
assert.strictEqual(P.compare(rows, "7258", "99"), null);
assert.strictEqual(P.compare(rows, "7258", "7258"), null);
assert.strictEqual(P.compare([], "1", "2"), null);

// 1.44 y 1.43 se ven iguales (1.4): no se marca a nadie como mejor ni se escribe "marca más (1.4 contra 1.4)"
const close = P.compare([{ team_id: "1", name: "Uno", pos: 1, pts: 30, pj: 25, gf: 36, gc: 20, dg: 16 }, { team_id: "2", name: "Dos", pos: 2, pts: 29, pj: 21, gf: 30, gc: 20, dg: 10 }], "1", "2");
assert.strictEqual(close.rows.find((r) => r.label === "Goles a favor por partido").better, null);
assert.ok(!P.headline(close).join(" ").includes("marca más"));

const h = P.headline(c);
assert.strictEqual(h[0], "Municipal llega 1.º con 28 puntos; Comunicaciones llega 2.º con 27.");
assert.strictEqual(h[1], "Municipal marca más (2.0 goles por partido contra 1.5) y recibe menos (0.9 contra 1.0).");
assert.deepStrictEqual(P.headline(null), []);
// ataque de uno y defensa del otro: dos nombres
const split = P.compare([{ team_id: "1", name: "Uno", pos: 1, pts: 10, pj: 5, gf: 10, gc: 8, dg: 2 }, { team_id: "2", name: "Dos", pos: 2, pts: 9, pj: 5, gf: 6, gc: 3, dg: 3 }], "1", "2");
assert.strictEqual(P.headline(split)[1], "Uno marca más (2.0 goles por partido contra 1.2); Dos recibe menos (0.6 contra 1.6).");

assert.deepStrictEqual(P.topScorers([{ name: "A", goals: 1 }, { name: "B", goals: 4 }, { name: "C", goals: 0 }, { name: "D", goals: 4 }, { name: "E", goals: 2 }, { name: "F", goals: 3 }], 3),
  [{ name: "B", goals: 4 }, { name: "D", goals: 4 }, { name: "F", goals: 3 }]);
assert.deepStrictEqual(P.topScorers([{ name: "A", goals: 0 }]), []);
assert.deepStrictEqual(P.topScorers(null), []);

const ms = [1, 2, 3, 4, 5, 6].map((i) => ({ id: String(i), state: "post", postponed: false, result: "GEP"[i % 3], start: `2026-0${i}-01T00:00:00Z`,
  home: { id: "7258", name: "Municipal", score: i }, away: { id: String(100 + i), name: `R${i}`, score: 0 } }));
ms.push({ id: "x", state: "pre", result: null, start: "2026-09-01T00:00:00Z", home: { id: "7258" }, away: { id: "1" } });
const f = P.recentForm(ms, "7258", 5);
assert.deepStrictEqual(f.map((x) => x.vs), ["R2", "R3", "R4", "R5", "R6"]);   // los 5 más recientes, el más viejo primero
assert.strictEqual(f[4].score, "6-0");
assert.strictEqual(f[0].home, true);
assert.deepStrictEqual(P.recentForm(null, "1"), []);
console.log("previa.test.js: OK");
