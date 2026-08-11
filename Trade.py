from dataclasses import dataclass, field
from typing import Dict, Optional


PEAK_AGE = 27
DOLLAR_PER_PERFORMANCE_POINT = 150_000


@dataclass
class Player:
    name: str
    stats: Dict[str, float]
    age: int
    contract_length: int
    salary: Optional[float] = None


def performance_score(player: Player) -> float:
    if not player.stats:
        return 0.0
    return sum(player.stats.values()) / len(player.stats)


def age_factor(player: Player) -> float:
    # Value peaks at PEAK_AGE and decays 3% per year of distance from it.
    distance = abs(player.age - PEAK_AGE)
    return max(0.4, 1 - distance * 0.03)


def contract_factor(player: Player) -> float:
    # Longer remaining control adds trade value, capped at 5 years.
    return 1 + min(player.contract_length, 5) * 0.05


def market_value(player: Player) -> float:
    return (
        performance_score(player)
        * age_factor(player)
        * contract_factor(player)
        * DOLLAR_PER_PERFORMANCE_POINT
    )


def final_value(player: Player, cap_percentage: Optional[float] = None) -> float:
    value = market_value(player)
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


def recommendation(player_a: Player, value_a: float, player_b: Player, value_b: float) -> str:
    diff = value_a - value_b
    threshold = 0.05 * max(value_a, value_b, 1)
    if abs(diff) <= threshold:
        return "Trade is balanced — neither side gains a significant advantage."
    higher, lower = (player_a, player_b) if diff > 0 else (player_b, player_a)
    return (
        f"{higher.name} carries greater trade value than {lower.name} — "
        f"the team acquiring {higher.name} benefits more from this trade."
    )


def compare_trade(player_a: Player, player_b: Player, salary_cap: Optional[float] = None) -> dict:
    market_a = market_value(player_a)
    market_b = market_value(player_b)

    cap_pct_a = player_a.salary / salary_cap * 100 if salary_cap and player_a.salary is not None else None
    cap_pct_b = player_b.salary / salary_cap * 100 if salary_cap and player_b.salary is not None else None
    final_a = final_value(player_a, cap_pct_a)
    final_b = final_value(player_b, cap_pct_b)

    result = {
        "player_a": {
            "name": player_a.name,
            "market_value": round(market_a, 2),
            "final_value": round(final_a, 2),
        },
        "player_b": {
            "name": player_b.name,
            "market_value": round(market_b, 2),
            "final_value": round(final_b, 2),
        },
        "trade_fairness_score": round(trade_fairness_score(final_a, final_b), 2),
        "recommendation": recommendation(player_a, final_a, player_b, final_b),
    }
    if player_a.salary is not None:
        result["player_a"]["salary"] = player_a.salary
    if player_b.salary is not None:
        result["player_b"]["salary"] = player_b.salary
    if cap_pct_a is not None:
        result["player_a"]["cap_percentage"] = round(cap_pct_a, 2)
    if cap_pct_b is not None:
        result["player_b"]["cap_percentage"] = round(cap_pct_b, 2)
    return result


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

    result = compare_trade(player_a, player_b)
    print("\n--- Results ---")
    for key, value in result.items():
        print(f"{key}: {value}")
