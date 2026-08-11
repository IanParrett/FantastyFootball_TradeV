from dataclasses import dataclass, field
from typing import Dict, List, Optional


PEAK_AGE = 27
DOLLAR_PER_PERFORMANCE_POINT = 200_000

# Points per unit for standard fantasy scoring, keyed by the friendly stat
# labels sleeper.py assigns. "Receptions" is handled separately since its
# value depends on the league's PPR setting.
STAT_POINTS = {
    "Passing Yards": 0.04,
    "Passing TDs": 4,
    "Interceptions Thrown": -2,
    "Rushing Yards": 0.1,
    "Rushing TDs": 6,
    "Fumbles Lost": -2,
    "Receiving Yards": 0.1,
    "Receiving TDs": 6,
    "Field Goals Made": 3,
    "Extra Points Made": 1,
    "Sacks": 1,
    "Interceptions": 2,
    "Fumble Recoveries": 2,
    "Forced Fumbles": 1,
    "Defensive TDs": 6,
    "Blocked Kicks": 2,
}


@dataclass
class LeagueSettings:
    ppr: float = 0.5  # points per reception: 0 = standard, 0.5 = half, 1 = full
    te_premium: bool = False
    te_premium_bonus: float = 0.5  # extra points per TE reception on top of ppr
    superflex: bool = False
    superflex_qb_multiplier: float = 1.4


@dataclass
class Player:
    name: str
    stats: Dict[str, float]
    age: int
    contract_length: int
    salary: Optional[float] = None
    position: Optional[str] = None


def performance_score(player: Player, settings: LeagueSettings) -> float:
    if not player.stats:
        return 0.0
    total = 0.0
    for label, value in player.stats.items():
        if label == "Receptions":
            total += value * settings.ppr
            if settings.te_premium and player.position == "TE":
                total += value * settings.te_premium_bonus
            continue
        total += value * STAT_POINTS.get(label, 0.0)
    return total


def age_factor(player: Player) -> float:
    # Value peaks at PEAK_AGE and decays 3% per year of distance from it.
    distance = abs(player.age - PEAK_AGE)
    return max(0.4, 1 - distance * 0.03)


def contract_factor(player: Player) -> float:
    # Longer remaining control adds trade value, capped at 5 years.
    return 1 + min(player.contract_length, 5) * 0.05


def market_value(player: Player, settings: LeagueSettings) -> float:
    value = (
        performance_score(player, settings)
        * age_factor(player)
        * contract_factor(player)
        * DOLLAR_PER_PERFORMANCE_POINT
    )
    if settings.superflex and player.position == "QB":
        # A 2nd startable QB slot makes every QB significantly scarcer.
        value *= settings.superflex_qb_multiplier
    return value


def final_value(player: Player, settings: LeagueSettings, cap_percentage: Optional[float] = None) -> float:
    value = market_value(player, settings)
    if cap_percentage is not None:
        # A player eating a bigger slice of the cap surrenders that much
        # of their market value back as trade cost.
        return value * (1 - cap_percentage / 100)
    if player.salary is not None:
        return value - player.salary
    return value


def trade_fairness_score(value_a: float, value_b: float) -> float:
    # Magnitude-based so it stays sane even when a value goes negative
    # (a player's salary can outweigh their market value).
    scale = max(abs(value_a), abs(value_b), 1)
    fairness = 100 - (abs(value_a - value_b) / scale) * 100
    return max(0.0, fairness)


def value_share(value_a: float, value_b: float) -> tuple:
    # Negative final value contributes no share (a side that's underwater
    # on cap cost doesn't get credit for it).
    a, b = max(value_a, 0.0), max(value_b, 0.0)
    total = a + b
    if total == 0:
        return 50.0, 50.0
    share_a = a / total * 100
    return round(share_a, 2), round(100 - share_a, 2)


def recommendation(label_a: str, value_a: float, label_b: str, value_b: float) -> str:
    diff = value_a - value_b
    threshold = 0.05 * max(value_a, value_b, 1)
    if abs(diff) <= threshold:
        return "Trade is balanced — neither side gains a significant advantage."
    higher, lower = (label_a, label_b) if diff > 0 else (label_b, label_a)
    return (
        f"{higher} carries greater total trade value than {lower} — "
        f"the side acquiring {higher}'s players benefits more from this trade."
    )


def _team_breakdown(
    players: List[Player], settings: LeagueSettings, salary_cap: Optional[float] = None
) -> dict:
    player_details = []
    total_market = 0.0
    total_final = 0.0

    for player in players:
        market = market_value(player, settings)
        cap_pct = (
            player.salary / salary_cap * 100
            if salary_cap and player.salary is not None
            else None
        )
        final = final_value(player, settings, cap_pct)
        total_market += market
        total_final += final

        detail = {
            "name": player.name,
            "market_value": round(market, 2),
            "final_value": round(final, 2),
        }
        if player.salary is not None:
            detail["salary"] = player.salary
        if cap_pct is not None:
            detail["cap_percentage"] = round(cap_pct, 2)
            if cap_pct > 0:
                detail["value_per_cap_percent"] = round(market / cap_pct, 2)
        player_details.append(detail)

    return {
        "players": player_details,
        "total_market_value": round(total_market, 2),
        "total_final_value": round(total_final, 2),
    }


def compare_trade(
    team_a: List[Player],
    team_b: List[Player],
    settings: Optional[LeagueSettings] = None,
    salary_cap: Optional[float] = None,
) -> dict:
    settings = settings or LeagueSettings()
    side_a = _team_breakdown(team_a, settings, salary_cap)
    side_b = _team_breakdown(team_b, settings, salary_cap)
    final_a = side_a["total_final_value"]
    final_b = side_b["total_final_value"]
    share_a, share_b = value_share(final_a, final_b)
    side_a["value_share"] = share_a
    side_b["value_share"] = share_b

    return {
        "team_a": side_a,
        "team_b": side_b,
        "trade_fairness_score": round(trade_fairness_score(final_a, final_b), 2),
        "recommendation": recommendation("Team One", final_a, "Team Two", final_b),
    }


def prompt_float(message: str) -> float:
    while True:
        try:
            return float(input(message))
        except ValueError:
            print("Please enter a number.")


def prompt_int(message: str) -> int:
    while True:
        try:
            return int(input(message))
        except ValueError:
            print("Please enter a whole number.")


def prompt_stats() -> Dict[str, float]:
    stats = {}
    print("Enter stat name and value (leave stat name blank to finish):")
    while True:
        stat_name = input("  Stat name: ").strip()
        if not stat_name:
            break
        stats[stat_name] = prompt_float(f"  {stat_name} value: ")
    return stats


def prompt_player(label: str, is_salary_league: bool) -> Player:
    print(f"\n--- {label} ---")
    name = input("Player name: ").strip() or label
    stats = prompt_stats()
    salary = prompt_float("League salary: ") if is_salary_league else None
    age = prompt_int("Age: ")
    contract_length = prompt_int("Contract length (years remaining): ")
    return Player(name=name, stats=stats, salary=salary, age=age, contract_length=contract_length)


def prompt_yes_no(message: str) -> bool:
    while True:
        answer = input(message).strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter y or n.")


if __name__ == "__main__":
    is_salary_league = prompt_yes_no("Is this a salary-cap league? (y/n): ")
    player_a = prompt_player("Player A", is_salary_league)
    player_b = prompt_player("Player B", is_salary_league)

    settings = LeagueSettings(superflex=prompt_yes_no("Is this a superflex/2QB league? (y/n): "))

    result = compare_trade([player_a], [player_b], settings)
    print("\n--- Results ---")
    for key, value in result.items():
        print(f"{key}: {value}")
