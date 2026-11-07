const assert = require("assert");
const L = require("../site/liguilla.js");
const names = ["A","B","C","D","E","F","G","H","I","J","K","L"];
const mk = (pts, pj) => names.map((n, i) => ({ team_id: String(i + 1), name: n, pts: pts[i], pj: pj[i] == null ? pj : pj[i], is_municipal: n === "D" }));
const rows = mk([30,28,27,26,25,24,20,18,15,12,10,5], 12);

// llave
let b = L.bracket(rows, {});
assert.deepStrictEqual(b.rounds[0].ties.map(t => [t.hi.name, t.lo.name]), [["C","F"],["D","E"]]);
assert.strictEqual(b.rounds[1].ties[0].lo, null);
b = L.bracket(rows, { P1: 6, P2: 4 });
const [s1, s2] = b.rounds[1].ties;
assert.strictEqual(s1.hi.name, "A"); assert.strictEqual(s1.lo.name, "F"); // peor ubicado (6.º) vs 1.º
assert.strictEqual(s2.hi.name, "B"); assert.strictEqual(s2.lo.name, "D");
assert.strictEqual(b.rounds[2].ties[0].hi, null);
b = L.bracket(rows, { P1: 3, P2: 4, S1: 4, S2: 2, F: 4 });
assert.strictEqual(b.champion.name, "D");
assert.strictEqual(b.rounds[2].ties[0].hi.name, "B");
// elecciones inválidas se descartan y las siguientes se limpian
b = L.bracket(rows, { P1: 3, P2: 4, S1: 9, S2: 4 });
assert.strictEqual(b.picks.S1, undefined);
assert.strictEqual(L.bracket(rows.slice(0, 4), {}), null);

// situación
let st = L.situation(mk([60,50,40,30,20,10,5,4,3,2,1,0], 20));
assert.strictEqual(st[0].status, "direct");
assert.strictEqual(st[11].status, "out");
assert.strictEqual(st[0].left, 2);
assert.strictEqual(st[0].max, 66);
st = L.situation(rows);
assert.ok(st.every(t => t.status === "alive"));
assert.strictEqual(L.situation([{ name: "X", pts: null, pj: null }])[0].status, "unknown");

// progreso
const pr = L.progress(mk([1,1,1,1,1,1,1,1,1,1,1,1], [22,22,20,20,21,21,22,22,22,22,22,22]));
assert.strictEqual(pr.minPJ, 20); assert.strictEqual(pr.matchesLeft, 3); assert.strictEqual(pr.done, false);
assert.strictEqual(L.progress(mk(Array(12).fill(1), 22)).done, true);
assert.strictEqual(L.progress([]), null);

// resumen
let sm = L.summary(rows).join(" ");
assert.ok(sm.includes("4.º con 26 puntos"));
assert.ok(sm.includes("ronda previa contra el 5.º (E) y cerraría de local"));
const r2 = mk([30,28,27,26,25,24,20,18,15,12,10,5], 12).map((r, i) => ({ ...r, is_municipal: i === 7 }));
sm = L.summary(r2).join(" ");
assert.ok(sm.includes("quedaría fuera"));
console.log("liguilla.test.js: OK");
