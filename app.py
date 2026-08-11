from flask import Flask, render_template, request, jsonify

import sleeper
import Trade

app = Flask(__name__)


def _build_player(data: dict) -> Trade.Player:
    salary = data.get("salary")
    stats = {
        stat["name"]: float(stat["value"])
        for stat in data.get("stats", [])
        if stat.get("name")
    }
    return Trade.Player(
        name=(data.get("name") or "Player").strip(),
        stats=stats,
        age=int(data.get("age") or 0),
        contract_length=int(data.get("contract_length") or 0),
        salary=float(salary) if salary not in (None, "") else None,
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/compare", methods=["POST"])
def api_compare():
    data = request.get_json(force=True)
    player_a = _build_player(data.get("player_a", {}))
    player_b = _build_player(data.get("player_b", {}))
    salary_cap = data.get("salary_cap")
    salary_cap = float(salary_cap) if salary_cap not in (None, "") else None
    return jsonify(Trade.compare_trade(player_a, player_b, salary_cap))


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
