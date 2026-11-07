const assert = require("assert");
const T = require("../site/topics.js");
const t = (title, summary = "") => T.topicsOf({ title, summary });

assert.deepStrictEqual(t("Municipal anuncia el fichaje de un delantero"), ["fichajes"]);
assert.ok(t("Rojos renuevan a su portero hasta 2027").includes("fichajes"));
assert.ok(t("Refuerzo extranjero llega a Municipal").includes("fichajes"));
assert.deepStrictEqual(t("Baja por lesión: desgarro de Martínez"), ["lesiones"]);
assert.ok(t("Capitán de Municipal fue operado y estará dos meses fuera").includes("lesiones"));
assert.ok(t("Conferencia de prensa del técnico tras la derrota").includes("tecnico"));
assert.ok(t("La junta directiva presenta al nuevo entrenador").includes("tecnico"));
assert.ok(t("Cuatro rojos fueron convocados a la Selección de Guatemala").includes("seleccion"));
assert.ok(t("La Bicolor convoca para las eliminatorias").includes("seleccion"));

// varios temas y acentos
const multi = t("Técnico confirma la lesión de un delantero y pide refuerzos");
assert.deepStrictEqual(multi.sort(), ["fichajes", "lesiones", "tecnico"]);
assert.ok(t("SELECCIÓN SUB-20 convoca").includes("seleccion"));

// sin tema; sin confundir palabras parecidas
assert.deepStrictEqual(t("Municipal vence 2-0 a Antigua en el Trébol"), []);
assert.deepStrictEqual(t("Resumen de la jornada 14 en la Liga Nacional"), []);
assert.deepStrictEqual(t("Los fichajes del año"), ["fichajes"]);
assert.deepStrictEqual(t("Ficha técnica del partido"), []);
assert.ok(t("Municipal fichó a un volante").includes("fichajes"));
assert.deepStrictEqual(t(null), []);
assert.deepStrictEqual(T.topicsOf(null), []);

// conteo y filtro
const items = [{ title: "Nuevo fichaje" }, { title: "Lesión de un titular" }, { title: "Resumen" }, { title: "Fichaje y lesión" }];
assert.deepStrictEqual(T.counts(items), { fichajes: 2, lesiones: 2, tecnico: 0, seleccion: 0 });
assert.strictEqual(T.filter(items, "fichajes").length, 2);
assert.strictEqual(T.filter(items, "all").length, 4);
assert.strictEqual(T.filter(null, "fichajes").length, 0);
assert.deepStrictEqual(T.TOPICS.map((x) => x.key), ["fichajes", "lesiones", "tecnico", "seleccion"]);
console.log("topics.test.js: OK");
