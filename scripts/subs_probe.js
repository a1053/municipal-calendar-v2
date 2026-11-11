const base = process.argv[2];
(async () => {
  const ms = (await (await fetch(`${base}/data/matches.json`)).json()).matches.filter((x) => x.detail);
  for (const m of ms) {
    let d; try { d = await (await fetch(`${base}/data/match/${m.id}.json`)).json(); } catch (e) { continue; }
    for (const lu of [...(d.lineups || []), ...((d.of && d.of.lineups) || [])]) {
      const names = lu.players.map((p) => `${p.starter ? "T" : "S"}:${p.jersey}:${p.name}`);
      const dup = lu.players.filter((p, i) => lu.players.findIndex((q) => q.name === p.name) !== i).map((p) => p.name);
      if (dup.length || /Bantes/.test(names.join())) console.log(m.start.slice(0, 10), m.home.name, "vs", m.away.name, "|", lu.team, lu.manual ? "[manual]" : "", "dup:", dup.join(",") || "-", "|", names.filter((n) => /Bantes/.test(n)).join(" ; "));
    }
  }
})();
