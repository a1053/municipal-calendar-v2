"""Probabilidades de clasificar a la liguilla (simulación Monte Carlo).

Modelo (simple y explicable):
  1. Fuerza de cada equipo: goles a favor y en contra por partido, ajustados hacia el
     promedio de la liga con un "peso previo" (pocos partidos = menos confianza).
  2. Goles esperados de cada partido = promedio de la liga x ataque propio x defensa
     rival, con ventaja de local. Los goles se sortean con una distribución Poisson.
  3. Partidos que faltan: los del calendario de la liga (ESPN) si están; los que no
     tienen fecha (por ejemplo los aplazados) se completan con emparejamientos al azar
     entre los equipos a los que les falten partidos.
  4. Se juega lo que falta miles de veces y se cuenta cuántas veces cada equipo
     termina entre los 6 primeros (y entre los 2 primeros).

El desempate es puntos, diferencia de goles y goles a favor (supuesto: ESPN no lo
publica); si todo es igual se sortea.
"""
from __future__ import annotations

import hashlib
import math
import random

PRIOR_GAMES = 6        # partidos "de promedio" que se mezclan con lo real
HOME_BOOST = 1.18      # multiplicador de goles del local (el visitante usa 1 / esto)
DEFAULT_SIMS = 20000


def _poisson(rng: random.Random, lam: float) -> int:
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def strengths(rows: list[dict]) -> tuple[float, dict]:
    """(promedio de goles por equipo y partido, {id: (ataque, defensa)})."""
    pj = sum(r["pj"] or 0 for r in rows)
    gf = sum(r["gf"] or 0 for r in rows)
    mu = gf / pj if pj and gf else 1.1
    out = {}
    for r in rows:
        n = r["pj"] or 0
        att = ((r["gf"] or 0) + PRIOR_GAMES * mu) / (n + PRIOR_GAMES) / mu
        dfn = ((r["gc"] or 0) + PRIOR_GAMES * mu) / (n + PRIOR_GAMES) / mu
        out[r["team_id"]] = (att, dfn)
    return mu, out


def fixtures_from_scoreboard(obj: dict, ids: set[str]) -> list[tuple[str, str]]:
    """Partidos de liga aún no jugados: [(local, visitante)] con ids de equipos de la tabla."""
    out, seen = [], set()
    for ev in sorted((obj or {}).get("events", []), key=lambda e: str(e.get("date", ""))):
        comp = (ev.get("competitions") or [{}])[0]
        status = ((ev.get("status") or comp.get("status") or {}).get("type")) or {}
        if status.get("completed") or status.get("state") == "post":
            continue
        home = away = None
        for c in comp.get("competitors", []):
            tid = str((c.get("team") or {}).get("id", ""))
            if c.get("homeAway") == "home":
                home = tid
            elif c.get("homeAway") == "away":
                away = tid
        gid = str(ev.get("id", ""))
        if home in ids and away in ids and home != away and gid not in seen:
            seen.add(gid)
            out.append((home, away))
    return out


def complete_fixtures(rows: list[dict], known: list[tuple[str, str]], rounds: int,
                      rng: random.Random) -> tuple[list[tuple[str, str]], str]:
    """Calendario que falta + relleno aleatorio para los equipos con partidos sin fecha.

    Devuelve (partidos, modo) con modo: "calendario", "mixto" o "aleatorio".
    """
    left = {r["team_id"]: max(0, rounds - (r["pj"] or 0)) for r in rows}
    fixtures = []
    for h, a in known:  # el calendario nunca puede pasar de lo que le falta a cada equipo
        if left[h] > 0 and left[a] > 0:
            fixtures.append((h, a))
            left[h] -= 1
            left[a] -= 1
    filled = 0
    pool = [t for t, n in left.items() for _ in range(n)]
    for _ in range(200):  # reintenta hasta emparejar sin que un equipo juegue contra sí mismo
        rng.shuffle(pool)
        pairs = [(pool[i], pool[i + 1]) for i in range(0, len(pool) - 1, 2)]
        if all(a != b for a, b in pairs):
            break
    else:
        pairs = [(a, b) for a, b in pairs if a != b]
    fixtures += pairs
    filled = len(pairs)
    mode = "calendario" if not filled else ("aleatorio" if not known else "mixto")
    return fixtures, mode


def simulate(rows: list[dict], fixtures: list[tuple[str, str]], sims: int = DEFAULT_SIMS,
             qualify: int = 6, direct: int = 2, seed: int = 1) -> dict:
    rng = random.Random(seed)
    mu, st = strengths(rows)
    ids = [r["team_id"] for r in rows]
    idx = {t: i for i, t in enumerate(ids)}
    n = len(ids)
    base = [((r["pts"] or 0), (r["dg"] or 0), (r["gf"] or 0)) for r in rows]
    lam = []
    for h, a in fixtures:
        ah, dh = st[h]
        aa, da = st[a]
        lam.append((idx[h], idx[a], mu * HOME_BOOST * ah * da, mu / HOME_BOOST * aa * dh))
    qual = [0] * n
    dire = [0] * n
    first = [0] * n
    pos_count = [[0] * n for _ in range(n)]
    pts_sum = [0.0] * n
    for _ in range(sims):
        pts = [b[0] for b in base]
        dg = [b[1] for b in base]
        gf = [b[2] for b in base]
        for hi, ai, lh, la in lam:
            gh, ga = _poisson(rng, lh), _poisson(rng, la)
            gf[hi] += gh
            gf[ai] += ga
            dg[hi] += gh - ga
            dg[ai] += ga - gh
            if gh > ga:
                pts[hi] += 3
            elif gh < ga:
                pts[ai] += 3
            else:
                pts[hi] += 1
                pts[ai] += 1
        order = sorted(range(n), key=lambda i: (-pts[i], -dg[i], -gf[i], rng.random()))
        for pos, i in enumerate(order):
            pos_count[i][pos] += 1
            pts_sum[i] += pts[i]
            if pos < qualify:
                qual[i] += 1
            if pos < direct:
                dire[i] += 1
            if pos == 0:
                first[i] += 1
    pct = lambda c: round(100.0 * c / sims, 1)  # noqa: E731
    teams = []
    for r in rows:
        i = idx[r["team_id"]]
        dist = [pct(c) for c in pos_count[i]]
        teams.append({
            "team_id": r["team_id"], "name": r["name"], "logo": r.get("logo"),
            "is_municipal": bool(r.get("is_municipal")), "pos": r.get("pos"),
            "pts": r["pts"], "pj": r["pj"],
            "p_qualify": pct(qual[i]), "p_direct": pct(dire[i]), "p_first": pct(first[i]),
            "exp_pts": round(pts_sum[i] / sims, 1),
            "exp_pos": round(sum((p + 1) * c for p, c in enumerate(pos_count[i])) / sims, 1),
            "pos_dist": dist,
        })
    return {"sims": sims, "teams": teams}


def build_odds(rows: list[dict], scoreboard: dict | None, rounds: int = 22, qualify: int = 6,
               direct: int = 2, sims: int = DEFAULT_SIMS) -> dict | None:
    """Arma odds.json. None si la tabla no sirve (faltan puntos o partidos jugados)."""
    rows = [r for r in rows if r.get("pj") is not None and r.get("pts") is not None]
    if len(rows) < qualify + 1:
        return None
    key = "|".join(f"{r['team_id']}:{r['pts']}:{r['pj']}:{r.get('gf')}:{r.get('gc')}" for r in rows)
    seed = int(hashlib.sha256(key.encode()).hexdigest()[:12], 16)  # mismos datos, mismo resultado
    rng = random.Random(seed)
    known = fixtures_from_scoreboard(scoreboard or {}, {r["team_id"] for r in rows})
    fixtures, mode = complete_fixtures(rows, known, rounds, rng)
    res = simulate(rows, fixtures, sims, qualify, direct, seed)
    res.update({"fixtures": mode, "fixtures_total": len(fixtures), "fixtures_known": len(known),
                "regular_rounds": rounds, "qualify": qualify, "direct": direct})
    return res
