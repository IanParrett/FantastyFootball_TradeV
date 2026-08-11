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
        ("pass_cmp", "Completions"),
        ("pass_att", "Pass Attempts"),
        ("pass_yd", "Passing Yards"),
        ("pass_td", "Passing TDs"),
        ("pass_int", "Interceptions Thrown"),
        ("pass_sack", "Times Sacked"),
        ("rush_att", "Rush Attempts"),
        ("rush_yd", "Rushing Yards"),
        ("rush_td", "Rushing TDs"),
        ("fum_lost", "Fumbles Lost"),
    ],
    "RB": [
        ("rush_att", "Rush Attempts"),
        ("rush_yd", "Rushing Yards"),
        ("rush_td", "Rushing TDs"),
        ("rec_tgt", "Targets"),
        ("rec", "Receptions"),
        ("rec_yd", "Receiving Yards"),
        ("rec_td", "Receiving TDs"),
        ("fum_lost", "Fumbles Lost"),
    ],
    "WR": [
        ("rec_tgt", "Targets"),
        ("rec", "Receptions"),
        ("rec_yd", "Receiving Yards"),
        ("rec_td", "Receiving TDs"),
        ("rush_att", "Rush Attempts"),
        ("rush_yd", "Rushing Yards"),
        ("rush_td", "Rushing TDs"),
        ("fum_lost", "Fumbles Lost"),
    ],
    "TE": [
        ("rec_tgt", "Targets"),
        ("rec", "Receptions"),
        ("rec_yd", "Receiving Yards"),
        ("rec_td", "Receiving TDs"),
        ("fum_lost", "Fumbles Lost"),
    ],
    "K": [
        ("fgm", "Field Goals Made"),
        ("fga", "Field Goals Attempted"),
        ("fgm_lng", "Longest Field Goal"),
        ("xpm", "Extra Points Made"),
        ("xpa", "Extra Point Attempts"),
    ],
    "DEF": [
        ("sack", "Sacks"),
        ("int", "Interceptions"),
        ("fum_rec", "Fumble Recoveries"),
        ("ff", "Forced Fumbles"),
        ("def_td", "Defensive TDs"),
        ("blk_kick", "Blocked Kicks"),
        ("pts_allow", "Points Allowed"),
        ("yds_allow", "Yards Allowed"),
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


def _display_name(player: dict):
    if player.get("full_name"):
        return player["full_name"]
    first, last = player.get("first_name"), player.get("last_name")
    if first or last:
        return " ".join(part for part in (first, last) if part)
    return None


def search_players(query: str, limit: int = 15) -> list:
    query = query.strip().lower()
    if not query:
        return []

    players = _get_players()
    matches = []
    for p in players.values():
        if p.get("position") not in FANTASY_POSITIONS:
            continue
        name = _display_name(p)
        if name and query in name.lower():
            matches.append((p, name))

    matches.sort(key=lambda pair: pair[0].get("search_rank") or 999999)
    matches = matches[:limit]

    return [
        {
            "id": p["player_id"],
            "name": name,
            "position": p.get("position"),
            "team": p.get("team"),
            "age": _age_from_birth_date(p.get("birth_date")),
        }
        for p, name in matches
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
        "name": _display_name(player),
        "position": player.get("position"),
        "team": player.get("team"),
        "age": _age_from_birth_date(player.get("birth_date")),
        "season": season,
        "stats": stats,
    }
