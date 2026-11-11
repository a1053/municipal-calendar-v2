const base = process.argv[2];
(async () => {
  const ms = (await (await fetch(`${base}/data/matches.json`)).json()).matches;
  const m = ms.find((x) => /Guastatoya/.test(x.home.name + x.away.name) && x.start.startsWith("2026-10-1"));
  console.log("partido", m.id, m.start, m.home.name, m.away.name);
  const d = await (await fetch(`${base}/data/match/${m.id}.json`)).json();
  const evs = [...(d.events || []).map((e) => ({ ...e, src: "ESPN" })), ...((d.of && d.of.events) || []).map((e) => ({ ...e, src: "OF" }))];
  evs.filter((e) => (e.kind === "goal" || e.kind === "own_goal")).forEach((e) => console.log(e.src, e.min, e.team, "|", [e.player, e.assist, e.kind].join(" | ")));
})();
