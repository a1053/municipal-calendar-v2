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

// marcas desde los eventos
const lu = { team_id: "7258", players: [
  { name: "Elvi Elington Cayetano", starter: true }, { name: "Rudy Barrientos", starter: true }, { name: "Jefry Bantes", starter: false }, { name: "Otro Nombre", starter: true }] };
const evs = [{ kind: "goal", player: "Elvi Elington", team_id: "7258" }, { kind: "goal", player: "Elvi Elington", team_id: "7258" },
  { kind: "yellow", player: "Rudy Barrientos", team_id: "7258" }, { kind: "yellow", player: "Otro Nombre", team_id: "99" },
  { kind: "sub", player: "Jefry Bantes", player_out: "Rudy Barrientos", team_id: "7258" }];
const mk2 = F.withMarks(lu, evs).players;
assert.deepStrictEqual(mk2[0].marks, ["goal", "goal"]);
assert.deepStrictEqual(mk2[1].marks, ["yellow", "out"]);
assert.deepStrictEqual(mk2[2].marks, ["in"]);
assert.strictEqual(mk2[3].marks, undefined);                      // la amarilla era del otro equipo
assert.strictEqual(F.withMarks({ ...lu, manual: true }, evs).players[0].marks, undefined);
assert.strictEqual(F.withMarks(lu, []), lu);
console.log("formation marks: OK");
