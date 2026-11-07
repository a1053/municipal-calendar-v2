const assert = require("assert");
const F = require("../site/forecast.js");
const near = (a, b, d = 0.01) => assert.ok(Math.abs(a - b) < d, `${a} != ${b}`);
const rows = [[20, 18], [28, 10], [15, 25], [22, 20]].map(([gf, gc], i) => ({ team_id: String(i + 1), pj: 10, gf, gc }));

// paridad con el cálculo equivalente en Python (mismo modelo que scripts/odds.py)
const f = F.forecast(rows, "1", "2");
near(f.xgHome, 1.6161, 0.001); near(f.xgAway, 1.9521, 0.001);
near(f.pHome, 32.32); near(f.pDraw, 21.75); near(f.pAway, 45.93);
near(f.pHome + f.pDraw + f.pAway, 100, 1e-6);
assert.strictEqual(f.topScores.length, 3);
assert.ok(f.topScores[0].p >= f.topScores[1].p && f.topScores[1].p >= f.topScores[2].p);

// el local pesa: intercambiar sedes cambia el resultado a favor del local
const g = F.forecast(rows, "2", "1");
assert.ok(g.pHome > F.forecast(rows, "1", "2").pAway);

// datos que faltan
assert.strictEqual(F.forecast(rows, "1", "99"), null);
assert.strictEqual(F.forecast(rows, "1", "1"), null);
assert.strictEqual(F.forecast([], "1", "2"), null);
assert.strictEqual(F.forecast([{ team_id: "1", pj: 1 }, { team_id: "2", pj: 1 }], "1", "2"), null);
console.log("forecast.test.js: OK");
