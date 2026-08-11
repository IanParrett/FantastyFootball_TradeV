import time

import requests

VALUES_URL = "https://api.fantasycalc.com/values/current"
CACHE_TTL_SECONDS = 12 * 60 * 60
NUM_TEAMS = 12

_cache = {}


def _cache_key(is_dynasty: bool, superflex: bool, ppr: float) -> tuple:
    return (is_dynasty, superflex, ppr)


def get_values(is_dynasty: bool, superflex: bool, ppr: float) -> dict:
    """Returns {sleeper_id: fantasycalc_value} for the given league settings."""
    key = _cache_key(is_dynasty, superflex, ppr)
    now = time.time()
    entry = _cache.get(key)
    if entry is None or now - entry["fetched_at"] > CACHE_TTL_SECONDS:
        params = {
            "isDynasty": str(is_dynasty).lower(),
            "numQbs": 2 if superflex else 1,
            "numTeams": NUM_TEAMS,
            "ppr": ppr,
        }
        try:
            response = requests.get(VALUES_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            # FantasyCalc unreachable - callers fall back to the formula-based value.
            return entry["data"] if entry else {}

        values = {
            str(p["player"]["sleeperId"]): p["value"]
            for p in data
            if p.get("player", {}).get("sleeperId")
        }
        entry = {"data": values, "fetched_at": now}
        _cache[key] = entry

    return entry["data"]
