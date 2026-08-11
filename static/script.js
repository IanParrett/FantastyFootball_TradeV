const statRowTemplate = document.getElementById("stat-row-template");
const salaryToggle = document.getElementById("salary-league-toggle");
const leagueFormatInputs = document.querySelectorAll('input[name="league-format"]');
const form = document.getElementById("trade-form");
const resultsSection = document.getElementById("results");

function isDynasty() {
  return document.querySelector('input[name="league-format"]:checked').value === "dynasty";
}

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

function addStatRow(panel, name = "", value = "") {
  const row = statRowTemplate.content.firstElementChild.cloneNode(true);
  row.querySelector(".stat-name").value = name;
  row.querySelector(".stat-value").value = value;
  row.querySelector(".remove-stat-btn").addEventListener("click", () => row.remove());
  panel.querySelector(".stats-list").appendChild(row);
}

function setStatRows(panel, stats) {
  panel.querySelector(".stats-list").innerHTML = "";
  const entries = Object.entries(stats);
  if (entries.length === 0) {
    addStatRow(panel);
    addStatRow(panel);
    return;
  }
  entries.forEach(([name, value]) => addStatRow(panel, name, value));
}

document.querySelectorAll(".add-stat-btn").forEach((btn) => {
  const panel = btn.closest(".panel");
  addStatRow(panel);
  addStatRow(panel);
  btn.addEventListener("click", () => addStatRow(panel));
});

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

document.querySelectorAll(".player-search").forEach((wrapper) => {
  const panel = wrapper.closest(".panel");
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
      panel.querySelector('input[name="age"]').value = detail.age;
    }
    setStatRows(panel, detail.stats || {});
  });

  document.addEventListener("click", (event) => {
    if (!wrapper.contains(event.target)) {
      list.classList.add("hidden");
    }
  });
});

salaryToggle.addEventListener("change", () => {
  document.querySelectorAll(".salary-field").forEach((field) => {
    field.classList.toggle("hidden", !salaryToggle.checked);
    field.querySelector("input").required = salaryToggle.checked;
  });
});

function collectPlayer(panel) {
  const stats = Array.from(panel.querySelectorAll(".stat-row"))
    .map((row) => ({
      name: row.querySelector(".stat-name").value.trim(),
      value: row.querySelector(".stat-value").value,
    }))
    .filter((s) => s.name && s.value !== "");

  return {
    name: panel.querySelector('input[name="name"]').value,
    age: panel.querySelector('input[name="age"]').value,
    contract_length: panel.querySelector('input[name="contract_length"]').value,
    salary: salaryToggle.checked ? panel.querySelector('input[name="salary"]').value : null,
    stats,
  };
}

function formatMoney(value) {
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function renderResults(result) {
  const showSalary = salaryToggle.checked;
  const cardHtml = (side, label) => `
    <div class="results-card">
      <h4>${result[side].name || label}</h4>
      <dl>
        <dt>Market value</dt><dd>${formatMoney(result[side].market_value)}</dd>
        ${showSalary ? `<dt>Salary</dt><dd>${formatMoney(result[side].salary ?? 0)}</dd>` : ""}
        ${showSalary ? `<dt>Final value</dt><dd>${formatMoney(result[side].final_value)}</dd>` : ""}
      </dl>
    </div>
  `;

  resultsSection.innerHTML = `
    <h3>Results</h3>
    <div class="results-grid">
      ${cardHtml("player_a", "Player One")}
      ${cardHtml("player_b", "Player Two")}
    </div>
    <div class="fairness">Trade fairness: ${result.trade_fairness_score}%</div>
    <p class="recommendation">${result.recommendation}</p>
  `;
  resultsSection.classList.remove("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resultsSection.classList.add("hidden");

  const payload = {
    player_a: collectPlayer(form.querySelector('[data-side="player_a"]')),
    player_b: collectPlayer(form.querySelector('[data-side="player_b"]')),
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
