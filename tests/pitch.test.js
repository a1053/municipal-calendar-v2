const assert = require("assert");
const P = require("../site/pitch.js");
const mk = (n, extra = {}) => Array.from({ length: n }, (_, i) => ({ name: `Jugador ${i + 1}`, jersey: String(i + 1), pos: i === 0 ? "G" : "D", starter: true, place: 0, ...extra }));

// 4-3-3 en orden: portero + 4 + 3 + 3
let rows = P.layout("4-3-3", mk(11));
assert.deepStrictEqual(rows.map((r) => r.length), [1, 4, 3, 3]);
assert.strictEqual(rows[0][0].jersey, "1");
assert.strictEqual(rows[3][2].jersey, "11");

// 4-2-3-1 (cuatro filas de campo)
assert.deepStrictEqual(P.layout("4-2-3-1", mk(11)).map((r) => r.length), [1, 4, 2, 3, 1]);

// se ordena por posición en la formación y el portero va primero aunque no sea el primero
const shuffled = mk(11).map((p, i) => ({ ...p, place: 11 - i, pos: i === 10 ? "G" : "M" })); // el de place 1 es el portero
rows = P.layout("4-4-2", shuffled);
assert.strictEqual(rows[0][0].pos, "G");
assert.strictEqual(rows[0][0].place, 1);

// portero fuera de lugar sin posiciones numeradas
const odd = mk(11); odd[0].pos = "D"; odd[5].pos = "GK";
assert.strictEqual(P.layout("4-4-2", odd)[0][0].jersey, "6");

// no se puede dibujar: formación mala, faltan titulares o suma incorrecta
assert.strictEqual(P.layout("", mk(11)), null);
assert.strictEqual(P.layout("4-3-3", mk(10)), null);
assert.strictEqual(P.layout("4-3-2", mk(11)), null);
assert.strictEqual(P.layout("raro", mk(11)), null);
assert.strictEqual(P.layout("4-3-3", [...mk(11), ...mk(3, { starter: false })]).flat().length, 11); // suplentes no cuentan

// nombres cortos
assert.strictEqual(P.shortName("José Carlos Martínez"), "Martínez");
assert.strictEqual(P.shortName("Nelson de la Cruz"), "de la Cruz");
assert.strictEqual(P.shortName("Pelé"), "Pelé");
assert.strictEqual(P.shortName(""), "");
console.log("pitch.test.js: OK");
assert.strictEqual(P.shortName("de León"), "de León");            // apellido compuesto sin nombre de pila
assert.strictEqual(P.shortName("Juan de la Cruz"), "de la Cruz");
console.log("pitch shortName apellidos: OK");
