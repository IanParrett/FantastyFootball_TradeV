const MAX_PLAYERS_PER_TEAM = 5;

const salaryToggle = document.getElementById("salary-league-toggle");
const leagueFormatInputs = document.querySelectorAll('input[name="league-format"]');
const form = document.getElementById("trade-form");
const resultsSection = document.getElementById("results");
const playerSlotTemplate = document.getElementById("player-slot-template");
const salaryCapField = document.querySelector(".salary-cap-field");
const salaryCapInput = document.getElementById("salary-cap-input");
const superflexToggle = document.getElementById("superflex-toggle");

function isDynasty() {
  return document.querySelector('input[name="league-format"]:checked').value === "dynasty";
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function setPlayerStats(slot, stats) {
  const entries = Object.entries(stats).map(([name, value]) => ({ name, value }));
  slot.querySelector(".stats-data").value = JSON.stringify(entries);
}

function getPlayerStats(slot) {
  try {
    return JSON.parse(slot.querySelector(".stats-data").value || "[]");
  } catch (err) {
    return [];
  }
}

function wirePlayerSearch(slot) {
  const wrapper = slot.querySelector(".player-search");
  const input = wrapper.querySelector('input[name="name"]');
  const list = wrapper.querySelector(".player-suggestions");

  const runSearch = debounce(async (query) => {
    if (!query.trim()) {
      list.classList.add("hidden");
      list.innerHTML = "";
      return;
    }
    const response = await fetch(`/api/players/search?q=${encodeURIComponent(query)}`);
    const players = response.ok ? await response.json() : [];

    if (players.length === 0) {
      list.classList.add("hidden");
      list.innerHTML = "";
      return;
    }

    list.innerHTML = players
      .map(
        (p) =>
          `<li data-id="${p.id}"><span>${p.name}</span><span class="suggestion-meta">${p.position ?? ""} ${p.team ?? "FA"}</span></li>`
      )
      .join("");
    list.classList.remove("hidden");
  }, 250);

  input.addEventListener("input", () => runSearch(input.value));

  list.addEventListener("click", async (event) => {
    const item = event.target.closest("li[data-id]");
    if (!item) return;

    list.classList.add("hidden");
    const response = await fetch(`/api/players/${item.dataset.id}`);
    if (!response.ok) return;
    const detail = await response.json();

    input.value = detail.name;
    if (detail.age != null) {
      slot.querySelector('input[name="age"]').value = detail.age;
    }
    slot.querySelector('input[name="position"]').value = detail.position || "";
    slot.querySelector('input[name="sleeper_id"]').value = detail.id || "";
    setPlayerStats(slot, detail.stats || {});
  });

  document.addEventListener("click", (event) => {
    if (!wrapper.contains(event.target)) {
      list.classList.add("hidden");
    }
  });
}

function applyCurrentToggles(slot) {
  const dynasty = isDynasty();
  const contractField = slot.querySelector(".contract-field");
  contractField.classList.toggle("hidden", !dynasty);
  contractField.querySelector("input").required = dynasty;

  const salaryField = slot.querySelector(".salary-field");
  salaryField.classList.toggle("hidden", !salaryToggle.checked);
  salaryField.querySelector("input").required = salaryToggle.checked;
}

function updateSlotControls(panel) {
  const slots = panel.querySelectorAll(".player-slot");
  slots.forEach((slot) => {
    slot.querySelector(".remove-player-btn").classList.toggle("hidden", slots.length <= 1);
  });
  panel.querySelector(".add-player-btn").disabled = slots.length >= MAX_PLAYERS_PER_TEAM;
}

function addPlayerSlot(panel) {
  const slot = playerSlotTemplate.content.firstElementChild.cloneNode(true);
  panel.querySelector(".players-list").appendChild(slot);

  wirePlayerSearch(slot);
  applyCurrentToggles(slot);
  slot.querySelector(".remove-player-btn").addEventListener("click", () => {
    slot.remove();
    updateSlotControls(panel);
  });

  updateSlotControls(panel);
  return slot;
}

document.querySelectorAll(".panel").forEach((panel) => {
  addPlayerSlot(panel);
  panel.querySelector(".add-player-btn").addEventListener("click", () => addPlayerSlot(panel));
});

leagueFormatInputs.forEach((input) => {
  input.addEventListener("change", () => {
    const dynasty = isDynasty();
    document.querySelectorAll(".contract-field").forEach((field) => {
      field.classList.toggle("hidden", !dynasty);
      const contractInput = field.querySelector("input");
      contractInput.required = dynasty;
      if (!dynasty) {
        contractInput.value = "0";
      }
    });
  });
});

salaryToggle.addEventListener("change", () => {
  document.querySelectorAll(".salary-field").forEach((field) => {
    field.classList.toggle("hidden", !salaryToggle.checked);
    field.querySelector("input").required = salaryToggle.checked;
  });
  salaryCapField.classList.toggle("hidden", !salaryToggle.checked);
});

function collectPlayer(slot) {
  return {
    name: slot.querySelector('input[name="name"]').value,
    age: slot.querySelector('input[name="age"]').value,
    position: slot.querySelector('input[name="position"]').value,
    sleeper_id: slot.querySelector('input[name="sleeper_id"]').value,
    contract_length: slot.querySelector('input[name="contract_length"]').value,
    salary: salaryToggle.checked ? slot.querySelector('input[name="salary"]').value : null,
    stats: getPlayerStats(slot),
  };
}

function collectTeam(panel) {
  return Array.from(panel.querySelectorAll(".player-slot"))
    .map(collectPlayer)
    .filter((p) => p.name.trim() !== "");
}

function formatMoney(value) {
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function formatLeagueDollars(value) {
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function playerRowHtml(p, showSalary) {
  const sourceLabel = p.value_source === "fantasycalc" ? "FantasyCalc" : "estimated";
  return `
    <div class="player-result">
      <div class="player-result-header">
        <span class="player-result-name">${p.name}</span>
        <span class="player-result-value">${formatMoney(p.market_value)}</span>
      </div>
      <span class="value-source-tag value-source-${p.value_source}">${sourceLabel}</span>
      ${
        p.league_dollar_value != null
          ? `<div class="worth-compare-block">
              ${
                p.auction_price != null
                  ? `<div class="worth-compare-row">
                      <span>Auction Price${p.expected_source === "espn" ? " (ESPN)" : ""}</span>
                      <strong>${formatLeagueDollars(p.auction_price)}</strong>
                    </div>`
                  : ""
              }
              ${
                p.salary != null
                  ? `<div class="worth-compare-row">
                      <span>League Salary</span>
                      <strong>${formatLeagueDollars(p.salary)}</strong>
                    </div>`
                  : ""
              }
              <div class="worth-compare-row worth-compare-highlight">
                <span>Worth to You</span>
                <strong>${formatLeagueDollars(p.league_dollar_value)}</strong>
              </div>
            </div>`
          : ""
      }
      ${
        showSalary
          ? `<div class="player-result-detail">
              ${p.cap_percentage != null ? `<span>${p.cap_percentage}% of cap</span>` : ""}
              ${p.value_per_cap_percent != null ? `<span>${formatMoney(p.value_per_cap_percent)} / 1% cap</span>` : ""}
              <span>Final: ${formatMoney(p.final_value)}</span>
            </div>`
          : ""
      }
    </div>
  `;
}

function teamCardHtml(team, label, showSalary) {
  return `
    <div class="results-card">
      <div class="results-card-header">
        <h4>${label}</h4>
        <span class="value-share-badge">${team.value_share}%</span>
      </div>
      <div class="team-total">
        <span>Total market value</span><strong>${formatMoney(team.total_market_value)}</strong>
      </div>
      ${
        showSalary
          ? `<div class="team-total"><span>Total final value</span><strong>${formatMoney(team.total_final_value)}</strong></div>`
          : ""
      }
      ${
        team.total_league_dollar_value != null
          ? `<div class="team-total team-total-worth"><span>Total worth to you</span><strong>${formatLeagueDollars(team.total_league_dollar_value)}</strong></div>`
          : ""
      }
      <div class="player-results">
        ${team.players.map((p) => playerRowHtml(p, showSalary)).join("")}
      </div>
    </div>
  `;
}

function worthComparisonHtml(result) {
  const a = result.team_a.total_league_dollar_value;
  const b = result.team_b.total_league_dollar_value;
  if (a == null || b == null) return "";
  const diff = Math.abs(a - b);
  const higher = a > b ? "Team One" : b > a ? "Team Two" : null;
  return `
    <div class="worth-comparison">
      <h4>Are both sides getting a fair amount?</h4>
      <div class="worth-comparison-row">
        <div class="worth-comparison-side">
          <span>Team One gives up</span>
          <strong>${formatLeagueDollars(a)}</strong>
        </div>
        <div class="worth-comparison-side">
          <span>Team Two gives up</span>
          <strong>${formatLeagueDollars(b)}</strong>
        </div>
      </div>
      <p class="worth-comparison-verdict">
        ${
          higher
            ? `${higher} is giving up ${formatLeagueDollars(diff)} more in real value than they're getting back.`
            : "Both sides are giving up an equal amount of real value — a dead-even trade."
        }
      </p>
    </div>
  `;
}

function splitBarHtml(result) {
  const a = result.team_a.value_share;
  const b = result.team_b.value_share;
  return `
    <div class="split-bar">
      <div class="split-bar-fill split-bar-a" style="width: ${a}%">${a >= 12 ? `${a}%` : ""}</div>
      <div class="split-bar-fill split-bar-b" style="width: ${b}%">${b >= 12 ? `${b}%` : ""}</div>
    </div>
    <div class="split-bar-labels">
      <span>Team One</span>
      <span>Team Two</span>
    </div>
  `;
}

function renderResults(result) {
  const showSalary = salaryToggle.checked;

  resultsSection.innerHTML = `
    <h3>Results</h3>
    ${splitBarHtml(result)}
    <div class="results-grid">
      ${teamCardHtml(result.team_a, "Team One", showSalary)}
      ${teamCardHtml(result.team_b, "Team Two", showSalary)}
    </div>
    <div class="fairness">Trade fairness: ${result.trade_fairness_score}%</div>
    <p class="fairness-explainer">
      This compares the two sides' total values to each other, not whether any one
      player was individually over- or underpaid. Each player's own surplus or
      deficit (vs. their expected auction price) is already baked into their value
      above — fairness just measures how evenly the two final totals balance out.
    </p>
    <p class="recommendation">${result.recommendation}</p>
    ${worthComparisonHtml(result)}
  `;
  resultsSection.classList.remove("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resultsSection.classList.add("hidden");

  const payload = {
    team_a: collectTeam(form.querySelector('[data-side="team_a"]')),
    team_b: collectTeam(form.querySelector('[data-side="team_b"]')),
    salary_cap: salaryToggle.checked ? salaryCapInput.value : null,
    league_format: document.querySelector('input[name="league-format"]:checked').value,
    scoring_format: document.querySelector('input[name="scoring-format"]:checked').value,
    superflex: superflexToggle.checked,
  };

  try {
    const response = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`Server error (${response.status})`);
    }
    renderResults(await response.json());
  } catch (err) {
    resultsSection.innerHTML = `<p class="error-message">${err.message}</p>`;
    resultsSection.classList.remove("hidden");
  }
});

const toggleAuctionValuesBtn = document.getElementById("toggle-auction-values");
const auctionValuesPanel = document.getElementById("auction-values-panel");
const auctionValuesBody = document.getElementById("auction-values-body");
const positionTabs = document.querySelectorAll(".position-tab");
let currentAuctionPosition = "ALL";
let auctionValuesLoaded = false;

async function loadAuctionValues() {
  auctionValuesBody.innerHTML = `<tr><td colspan="5">Loading...</td></tr>`;
  const scoring = document.querySelector('input[name="scoring-format"]:checked').value;
  const response = await fetch(
    `/api/auction-values?scoring_format=${scoring}&position=${currentAuctionPosition}&superflex=${superflexToggle.checked}`
  );
  const players = response.ok ? await response.json() : [];

  if (players.length === 0) {
    auctionValuesBody.innerHTML = `<tr><td colspan="5">No data available.</td></tr>`;
    return;
  }

  auctionValuesBody.innerHTML = players
    .map(
      (p) => `
        <tr>
          <td>${p.rank}</td>
          <td>${p.name}</td>
          <td>${p.position}</td>
          <td>${p.team}</td>
          <td>${formatMoney(p.value)}</td>
        </tr>
      `
    )
    .join("");
}

toggleAuctionValuesBtn.addEventListener("click", () => {
  const isHidden = auctionValuesPanel.classList.toggle("hidden");
  toggleAuctionValuesBtn.textContent = isHidden ? "Show Auction Values" : "Hide Auction Values";
  if (!isHidden && !auctionValuesLoaded) {
    auctionValuesLoaded = true;
    loadAuctionValues();
  }
});

positionTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    positionTabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    currentAuctionPosition = tab.dataset.position;
    loadAuctionValues();
  });
});

document.querySelectorAll('input[name="scoring-format"]').forEach((input) => {
  input.addEventListener("change", () => {
    if (!auctionValuesPanel.classList.contains("hidden")) {
      loadAuctionValues();
    }
  });
});

superflexToggle.addEventListener("change", () => {
  if (!auctionValuesPanel.classList.contains("hidden")) {
    loadAuctionValues();
  }
});
