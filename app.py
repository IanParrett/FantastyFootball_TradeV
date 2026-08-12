from flask import Flask, render_template, request, jsonify

import espn
import fantasycalc
import sleeper
import Trade

app = Flask(__name__)


def _build_player(data: dict, scoring: str, espn_values: dict) -> Trade.Player:
    salary = data.get("salary")
    stats = {
        stat["name"]: float(stat["value"])
        for stat in data.get("stats", [])
        if stat.get("name")
    }
    name = (data.get("name") or "Player").strip()
    espn_entry = espn_values.get(espn.normalize_name(name))
    return Trade.Player(
        name=name,
        stats=stats,
        age=int(data.get("age") or 0),
        contract_length=int(data.get("contract_length") or 0),
        salary=float(salary) if salary not in (None, "") else None,
        position=data.get("position") or None,
        sleeper_id=data.get("sleeper_id") or None,
        espn_auction_value=espn_entry.get(scoring) if espn_entry else None,
    )


def _build_team(players_data: list, scoring: str, espn_values: dict) -> list:
    return [_build_player(p, scoring, espn_values) for p in players_data if p.get("name")]


def _build_settings(data: dict) -> Trade.LeagueSettings:
    scoring = data.get("scoring_format", "half_ppr")
    ppr = {"standard": 0.0, "half_ppr": 0.5, "full_ppr": 1.0}.get(scoring, 0.5)
    return Trade.LeagueSettings(
        ppr=ppr,
        superflex=bool(data.get("superflex")),
    )


def _get_fc_values(data: dict, settings: Trade.LeagueSettings) -> dict:
    is_dynasty = data.get("league_format") == "dynasty"
    try:
        return fantasycalc.get_values(is_dynasty, settings.superflex, settings.ppr)
    except Exception:
        return {}


def _get_espn_values() -> dict:
    try:
        return espn.get_auction_values()
    except Exception:
        return {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/compare", methods=["POST"])
def api_compare():
    data = request.get_json(force=True)
    settings = _build_settings(data)
    scoring = data.get("scoring_format", "half_ppr")
    espn_values = _get_espn_values()
    team_a = _build_team(data.get("team_a", []), scoring, espn_values)
    team_b = _build_team(data.get("team_b", []), scoring, espn_values)
    fc_values = _get_fc_values(data, settings)
    salary_cap = data.get("salary_cap")
    salary_cap = float(salary_cap) if salary_cap not in (None, "") else None
    return jsonify(Trade.compare_trade(team_a, team_b, settings, fc_values, salary_cap))


@app.route("/api/auction-values")
def api_auction_values():
    scoring = request.args.get("scoring_format", "half_ppr")
    position = request.args.get("position", "ALL")
    try:
        return jsonify(espn.get_ranked_players(scoring, position))
    except Exception:
        return jsonify([])


@app.route("/api/players/search")
def api_players_search():
    query = request.args.get("q", "")
    return jsonify(sleeper.search_players(query))


@app.route("/api/players/<player_id>")
def api_player_detail(player_id):
    detail = sleeper.get_player_detail(player_id)
    if detail is None:
        return jsonify({"error": "Player not found"}), 404
    return jsonify(detail)


if __name__ == "__main__":
    app.run(debug=True)
