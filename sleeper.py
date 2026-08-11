import time
from datetime import date

import requests

PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
STATS_URL = "https://api.sleeper.app/v1/stats/nfl/regular/{season}"
DEFAULT_SEASON = 2025
CACHE_TTL_SECONDS = 12 * 60 * 60
FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF"}

# (raw Sleeper stat key, friendly label) per position, in the order they
# should be shown as stat rows.
STAT_FIELDS = {
    "QB": [
        ("pass_yd", "Passing Yards"),
        ("pass_td", "Passing TDs"),
        ("pass_int", "Interceptions"),
        ("rush_yd", "Rushing Yards"),
        ("rush_td", "Rushing TDs"),
    ],
    "RB": [
        ("rush_yd", "Rushing Yards"),
        ("rush_td", "Rushing TDs"),
        ("rec", "Receptions"),
        ("rec_yd", "Receiving Yards"),
        ("rec_td", "Receiving TDs"),
    ],
    "WR": [
        ("rec", "Receptions"),
        ("rec_yd", "Receiving Yards"),
        ("rec_td", "Receiving TDs"),
        ("rush_yd", "Rushing Yards"),
        ("rush_td", "Rushing TDs"),
    ],
    "TE": [
        ("rec", "Receptions"),
        ("rec_yd", "Receiving Yards"),
        ("rec_td", "Receiving TDs"),
    ],
    "K": [
        ("fgm", "Field Goals Made"),
        ("fga", "Field Goals Attempted"),
        ("xpm", "Extra Points Made"),
    ],
}

_players_cache = {"data": None, "fetched_at": 0.0}
_stats_cache = {}


def _get_players() -> dict:
    now = time.time()
    if _players_cache["data"] is None or now - _players_cache["fetched_at"] > CACHE_TTL_SECONDS:
        response = requests.get(PLAYERS_URL, timeout=30)
        response.raise_for_status()
        _players_cache["data"] = response.json()
        _players_cache["fetched_at"] = now
    return _players_cache["data"]


def _get_stats(season: int) -> dict:
    entry = _stats_cache.get(season)
    now = time.time()
    if entry is None or now - entry["fetched_at"] > CACHE_TTL_SECONDS:
        response = requests.get(STATS_URL.format(season=season), timeout=30)
        response.raise_for_status()
        entry = {"data": response.json(), "fetched_at": now}
        _stats_cache[season] = entry
    return entry["data"]


def _age_from_birth_date(birth_date: str):
    if not birth_date:
        return None
    year, month, day = (int(part) for part in birth_date.split("-"))
    today = date.today()
    age = today.year - year - ((today.month, today.day) < (month, day))
    return age


def search_players(query: str, limit: int = 15) -> list:
    query = query.strip().lower()
    if not query:
        return []

    players = _get_players()
    matches = [
        p
        for p in players.values()
        if p.get("position") in FANTASY_POSITIONS
        and p.get("full_name")
        and query in p["full_name"].lower()
    ]
    matches.sort(key=lambda p: p.get("search_rank") or 999999)
    matches = matches[:limit]

    return [
        {
            "id": p["player_id"],
            "name": p["full_name"],
            "position": p.get("position"),
            "team": p.get("team"),
            "age": _age_from_birth_date(p.get("birth_date")),
        }
        for p in matches
    ]


def get_player_detail(player_id: str, season: int = DEFAULT_SEASON) -> dict:
    players = _get_players()
    player = players.get(player_id)
    if player is None:
        return None

    season_stats = _get_stats(season).get(player_id, {})
    fields = STAT_FIELDS.get(player.get("position"), [])
    stats = {
        label: season_stats[key]
        for key, label in fields
        if season_stats.get(key) is not None
    }

    return {
        "id": player_id,
        "name": player.get("full_name"),
        "position": player.get("position"),
        "team": player.get("team"),
        "age": _age_from_birth_date(player.get("birth_date")),
        "season": season,
        "stats": stats,
    }
