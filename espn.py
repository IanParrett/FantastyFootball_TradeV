import re
import time

import requests

PLAYERS_URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/players"
SEASON = 2026
BUDGET = 200  # ESPN's auction values are calibrated to a standard $200 budget
CACHE_TTL_SECONDS = 12 * 60 * 60

_cache = {"data": None, "fetched_at": 0.0}

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
