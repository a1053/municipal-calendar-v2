const assert = require("assert");
const C = require("../site/sharecard.js");
const m = (state, hs, as, x = {}) => ({ state, status: "", home: { id: "1", name: "Municipal", score: hs }, away: { id: "2", name: "Antigua", score: as }, ...x });
const ev = [{ kind: "goal", player: "Pérez", min: "10'", team_id: "1" }, { kind: "goal", player: "Ruiz", min: "50'", team_id: "2", penalty: true },
  { kind: "own_goal", player: "Gómez", min: "70'", team_id: "1" }, { kind: "yellow", player: "X", min: "5'", team_id: "1" }];
const post = C.cardModel(m("post", 2, 1), ev, { competition: "Liga" });
assert.strictEqual(post.headline, "Final");
assert.deepStrictEqual(post.scorers.map((s) => s.text), ["Pérez", "Ruiz (p)", "Gómez (autogol)"]);
assert.deepStrictEqual(post.scorers.map((s) => s.home), [true, false, true]);
assert.strictEqual(post.home.score, 2);
const pre = C.cardModel(m("pre", null, null, { broadcasts: ["Tigo"] }), ev, { when: "sáb 7 p. m." });
assert.strictEqual(pre.home.score, null); assert.strictEqual(pre.scorers.length, 0);
assert.strictEqual(pre.when, "sáb 7 p. m."); assert.strictEqual(pre.tv, "Tigo");
assert.strictEqual(C.cardModel(m("in", 1, 0, { status: "65'" }), [], {}).headline, "En vivo 65'");
assert.strictEqual(C.cardModel(m("pre", null, null, { postponed: true }), [], {}).headline, "Aplazado");
assert.strictEqual(C.cardModel(m("post", 0, 0), Array(20).fill(ev[0]), {}).scorers.length, 6);
console.log("sharecard.test.js: OK");
