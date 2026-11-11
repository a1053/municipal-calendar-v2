const base = process.argv[2];
(async () => {
  const ms = (await (await fetch(`${base}/data/matches.json`)).json()).matches;
  for (const m of ms.filter((x) => /Cob|Guastatoya|Xelaj|Comunicaciones/.test(x.home.name + x.away.name) && x.state === "post")) {
    const d = await (await fetch(`${base}/data/match/${m.id}.json`)).json();
    for (const lu of d.lineups || []) {
      if (!lu.manual) continue;
      const names = lu.players.map((p) => `${p.starter ? "S" : "b"}${p.place}:${p.jersey}:${p.name}`);
      const dup = names.map((n) => n.split(":")[2]).filter((n, i, a) => a.indexOf(n) !== i);
      console.log(m.start.slice(0, 10), m.home.name, m.away.name, "|", lu.team, lu.formation, "dups:", dup.join(",") || "no");
      if (/Municipal/.test(lu.team)) console.log("   ", names.join(" | "));
    }
  }
})();
