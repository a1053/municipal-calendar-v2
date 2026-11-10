// Diagnóstico: ¿qué partidos publicados dibujan cancha y por qué los otros no?
const F = require("../site/formation.js"), P = require("../site/pitch.js");
const base = process.argv[2];
const get = async (p) => { const r = await fetch(`${base}/data/${p}`); if (!r.ok) throw new Error(`${p} ${r.status}`); return r.json(); };
(async () => {
  const ms = (await get("matches.json")).matches.filter((m) => m.detail);
  let roster = null; try { roster = (await get("roster.json")).players; } catch (e) { console.log("roster:", e.message); }
  console.log("roster", roster ? roster.length : "NO", "partidos con detalle", ms.length);
  for (const m of ms) {
    let d; try { d = await get(`match/${m.id}.json`); } catch (e) { console.log(m.id, "sin json"); continue; }
    const espn = d.lineups || [], of = (d.of && d.of.lineups) || [];
    const src = espn.length ? "ESPN" : of.length ? "OF" : "ninguna";
    const lus = espn.length ? espn : of;
    const mine = lus.find((l) => String(l.team_id) === "7258");
    let why = "";
    if (!mine) why = "sin alineación de Municipal";
    else {
      const st = mine.players.filter((p) => p.starter);
      if (mine.formation) { why = P.layout(mine.formation, mine.players) ? "dibuja (formación de la fuente)" : `formación ${mine.formation} pero no dibuja (titulares ${st.length}, place ${st.filter((p) => p.place > 0).length})`; }
      else if (st.length !== 11) why = `titulares ${st.length} (faltan para estimar)`;
      else if (!roster) why = "sin roster";
      else {
        const est = F.estimate(mine.players, roster);
        if (est) why = `estimada ${est.formation}`;
        else { const miss = st.filter((p) => !roster.some((r) => F.same(p.name, r.name))).map((p) => p.name); why = `NO estima; sin match: ${miss.join(", ") || "(conteo por posición raro)"}`; }
      }
    }
    console.log(`${m.start.slice(0, 10)} ${m.home.name} ${m.home.score ?? ""}-${m.away.score ?? ""} ${m.away.name} [${src}] ${why}`);
  }
})();
