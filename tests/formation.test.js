const assert = require("assert");
const F = require("../site/formation.js");
const P = require("../site/pitch.js");
const mk = (specs) => specs.map(([name, order, jersey]) => ({ name, pos_order: order, jersey }));
const roster = mk([["Portero Uno", 0, "1"], ["Carlos Pérez Ruiz", 1, "2"], ["Luis Gómez", 1, "3"], ["Juan Díaz", 1, "4"], ["Mario López", 1, "5"],
  ["Pedro Soto", 2, "6"], ["Ana Marín", 2, "8"], ["Rudy Barrientos", 2, "10"], ["Delantero Nueve", 3, "9"], ["Elvi Elington Cayetano", 3, "11"], ["Otro Extra", 3, "7"]]);
const st = (names) => names.map((n, i) => ({ name: n, jersey: String(i + 1), starter: true }));
const names = ["Portero Uno", "Carlos Pérez", "Luis Gómez", "Juan Díaz", "Mario López", "Pedro Soto", "Ana Marín", "Rudy Barrientos", "Delantero Nueve", "Elvi Elington", "Otro Extra"];
const r = F.estimate(st(names), roster);
assert.strictEqual(r.formation, "4-3-3");
assert.strictEqual(r.players[0].pos, "G");
assert.deepStrictEqual(P.layout(r.formation, r.players).map((x) => x.length), [1, 4, 3, 3]);   // lo dibuja pitch.js
assert.strictEqual(F.estimate(st(names.map((n, i) => (i === 3 ? "Desconocido Total" : n))), roster), null);  // un titular sin match: no se dibuja
assert.strictEqual(F.estimate(st(names).slice(0, 10), roster), null);
assert.strictEqual(F.estimate(st(names), []), null);
assert.ok(F.same("Rudy Barrientos", "Rudy Alexander Barrientos") && !F.same("Rudy Barrientos", "Rudy Muñoz"));
const bench = [...st(names), { name: "Suplente", starter: false }];
assert.strictEqual(F.estimate(bench, roster).players.length, 12);
console.log("formation.test.js: OK");
