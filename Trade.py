from dataclasses import dataclass, field
from typing import Dict


PEAK_AGE = 27
DOLLAR_PER_PERFORMANCE_POINT = 150_000


@dataclass
class Player:
    name: str
    stats: Dict[str, float]
    salary: float
    age: int
    contract_length: int


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


def trade_fairness_score(value_a: float, value_b: float) -> float:
    if value_a == 0 and value_b == 0:
        return 100.0
    return (min(value_a, value_b) / max(value_a, value_b)) * 100


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


def compare_trade(player_a: Player, player_b: Player) -> dict:
    value_a = market_value(player_a)
    value_b = market_value(player_b)

    return {
        "player_a": {
            "name": player_a.name,
            "market_value": round(value_a, 2),
        },
        "player_b": {
            "name": player_b.name,
            "market_value": round(value_b, 2),
        },
        "trade_fairness_score": round(trade_fairness_score(value_a, value_b), 2),
        "recommendation": recommendation(player_a, value_a, player_b, value_b),
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


def prompt_player(label: str) -> Player:
    print(f"\n--- {label} ---")
    name = input("Player name: ").strip() or label
    stats = prompt_stats()
    salary = prompt_float("League salary: ")
    age = prompt_int("Age: ")
    contract_length = prompt_int("Contract length (years remaining): ")
    return Player(name=name, stats=stats, salary=salary, age=age, contract_length=contract_length)


if __name__ == "__main__":
    player_a = prompt_player("Player A")
    player_b = prompt_player("Player B")

    result = compare_trade(player_a, player_b)
    print("\n--- Results ---")
    for key, value in result.items():
        print(f"{key}: {value}")
