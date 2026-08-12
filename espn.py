import re
import time

import requests

PLAYERS_URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/players"
SEASON = 2026
BUDGET = 200  # ESPN's auction values are calibrated to a standard $200 budget
CACHE_TTL_SECONDS = 12 * 60 * 60

_cache = {"data": None, "fetched_at": 0.0}

POSITION_MAP = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K"}

TEAM_MAP = {
    0: "FA", 1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL",
    7: "DEN", 8: "DET", 9: "GB", 10: "TEN", 11: "IND", 12: "KC", 13: "LV",
    14: "LAR", 15: "MIA", 16: "MIN", 17: "NE", 18: "NO", 19: "NYG",
    20: "NYJ", 21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC", 25: "SF",
    26: "SEA", 27: "TB", 28: "WSH", 29: "CAR", 30: "JAX", 33: "BAL",
    34: "HOU",
}

_SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")
_PUNCT_RE = re.compile(r"[.'']")
_SPACE_RE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower().strip()
    name = _PUNCT_RE.sub("", name)
    name = _SUFFIX_RE.sub("", name)
    name = _SPACE_RE.sub(" ", name).strip()
    return name


def _fetch_raw() -> list:
    now = time.time()
    if _cache["data"] is None or now - _cache["fetched_at"] > CACHE_TTL_SECONDS:
        headers = {
            "x-fantasy-filter": '{"players":{"filterActive":{"value":true}}}',
        }
        response = requests.get(
            PLAYERS_URL.format(season=SEASON),
            params={"scoringPeriodId": 0, "view": "kona_player_info"},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        _cache["data"] = response.json()
        _cache["fetched_at"] = now
    return _cache["data"]


def get_auction_values() -> dict:
    """Returns {normalized_name: {"standard": $, "half_ppr": $, "full_ppr": $}}
    calibrated to a $200 budget, built from ESPN's real draft auction values.
    """
    players = _fetch_raw()
    values = {}
    for p in players:
        ranks = p.get("draftRanksByRankType") or {}
        standard = ranks.get("STANDARD", {}).get("auctionValue")
        ppr = ranks.get("PPR", {}).get("auctionValue")
        if not standard and not ppr:
            continue
        standard = standard or ppr
        ppr = ppr or standard
        name = normalize_name(p.get("fullName"))
        if not name:
            continue
        values[name] = {
            "standard": standard,
            "half_ppr": (standard + ppr) / 2,
            "full_ppr": ppr,
        }
    return values


def get_auction_value(player_name: str, scoring_format: str) -> float:
    values = get_auction_values()
    entry = values.get(normalize_name(player_name))
    if entry is None:
        return None
    return entry.get(scoring_format)


def get_ranked_players(scoring_format: str, position: str = None, limit: int = 300) -> list:
    """Full list of players with a real auction value, sorted highest to
    lowest, for display as a reference table.
    """
    players = _fetch_raw()
    ranked = []
    for p in players:
        pos_id = p.get("defaultPositionId")
        pos = POSITION_MAP.get(pos_id)
        if pos is None:
            continue
        if position and position != "ALL" and pos != position:
            continue

        ranks = p.get("draftRanksByRankType") or {}
        standard = ranks.get("STANDARD", {}).get("auctionValue")
        ppr = ranks.get("PPR", {}).get("auctionValue")
        if not standard and not ppr:
            continue
        standard = standard or ppr
        ppr = ppr or standard
        value = {"standard": standard, "half_ppr": (standard + ppr) / 2, "full_ppr": ppr}.get(
            scoring_format, (standard + ppr) / 2
        )
        if not value:
            continue

        ranked.append(
            {
                "name": p.get("fullName"),
                "position": pos,
                "team": TEAM_MAP.get(p.get("proTeamId"), "FA"),
                "value": value,
            }
        )

    ranked.sort(key=lambda p: p["value"], reverse=True)
    for i, entry in enumerate(ranked[:limit], start=1):
        entry["rank"] = i
    return ranked[:limit]
