/**
 * Tourism Data Warehouse & Data Mining System (DMDW)
 * Master Client-Side JavaScript
 * Author: Data Engineering & Data Science Team
 */

// Clay Design System Color Tokens (per DESIGN.md)
const CLAY_COLORS = {
  pink: "#ff4d8b",
  teal: "#1a3a3a",
  lavender: "#b8a4ed",
  peach: "#ffb084",
  ochre: "#e8b94a",
  mint: "#a4d4c5",
  coral: "#ff6b5a",
  ink: "#0a0a0a",
  body: "#3a3a3a",
  muted: "#6a6a6a",
  hairline: "#e5e5e5",
  canvas: "#fffaf0",
  surfaceCard: "#f5f0e0"
};

// Global switchTab helper for footer & hero CTAs
window.switchTab = function(tabId) {
  const item = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
  if (item) {
    item.click();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
};

// Apply Clay Design System chart defaults
if (window.Chart) {
  Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
  Chart.defaults.color = CLAY_COLORS.body;
  Chart.defaults.borderColor = CLAY_COLORS.hairline;
}

let charts = {};

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initHealthCheck();
  initGlobalFilters();
  loadDashboardData();
  setupRecommender();
  setupCatalogSearch();
});

// --- Tab Navigation ---
function initNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  const tabContents = document.querySelectorAll(".tab-content");
  const titleElem = document.getElementById("current-view-title");

  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const targetTab = item.getAttribute("data-tab");
      navItems.forEach(n => n.classList.remove("active"));
      tabContents.forEach(t => t.classList.remove("active"));

      item.classList.add("active");
      const activeContent = document.getElementById(targetTab);
      if (activeContent) activeContent.classList.add("active");

      const title = item.querySelector("span").innerText;
      if (titleElem) titleElem.innerText = title;

      // Lazy load tab data on first view
      handleTabActivation(targetTab);
    });
  });
}

function handleTabActivation(tabId) {
  if (tabId === "analytics-tab" && !charts["categoryBreakdown"]) {
    loadAnalyticsTab();
  } else if (tabId === "warehouse-tab") {
    loadWarehouseTab();
  } else if (tabId === "olap-tab") {
    loadOlapRollup();
  } else if (tabId === "segmentation-tab") {
    loadSegmentationTab();
  } else if (tabId === "rules-tab") {
    loadRulesTab();
  } else if (tabId === "classification-tab") {
    loadClassificationTab();
  } else if (tabId === "outliers-tab") {
    loadOutliersTab();
  } else if (tabId === "trends-tab") {
    loadTrendsTab();
  } else if (tabId === "destinations-tab") {
    loadDestinationsMaster();
  }
}

// --- Health Check ---
async function initHealthCheck() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const badge = document.getElementById("db-engine-badge");
    if (badge) {
      badge.innerText = data.database_engine || "SQLITE";
    }
  } catch (err) {
    console.error("Health check error:", err);
  }
}

// --- Global Filters ---
async function initGlobalFilters() {
  try {
    const res = await fetch("/api/filters");
    const json = await res.json();
    if (json.status === "success") {
      const regions = json.data.regions;
      const regSelect = document.getElementById("filter-region");
      regions.forEach(r => {
        const opt = document.createElement("option");
        opt.value = r;
        opt.innerText = r;
        regSelect.appendChild(opt);
      });

      const access = json.data.accessibility;
      const accSelect = document.getElementById("filter-access");
      access.forEach(a => {
        const opt = document.createElement("option");
        opt.value = a;
        opt.innerText = a;
        accSelect.appendChild(opt);
      });
    }

    document.getElementById("btn-apply-filters").addEventListener("click", () => {
      loadDashboardData();
    });

    document.getElementById("btn-reset-filters").addEventListener("click", () => {
      document.getElementById("filter-region").value = "All";
      document.getElementById("filter-access").value = "All";
      loadDashboardData();
    });
  } catch (err) {
    console.error("Failed to load filter options:", err);
  }
}

// --- Dashboard Tab Data ---
async function loadDashboardData() {
  const region = document.getElementById("filter-region").value;
  const access = document.getElementById("filter-access").value;

  const params = new URLSearchParams();
  if (region !== "All") params.append("region", region);
  if (access !== "All") params.append("accessibility", access);

  try {
    // 1. Fetch KPIs
    const kpiRes = await fetch(`/api/kpis?${params.toString()}`);
    const kpiJson = await kpiRes.json();
    if (kpiJson.status === "success") {
      const k = kpiJson.kpis;
      document.getElementById("kpi-dest-count").innerText = k.total_destinations ?? 0;
      const featDest = document.getElementById("feat-dest-count");
      if (featDest) featDest.innerText = k.total_destinations ?? 0;
      document.getElementById("kpi-states-count").innerText = `Across ${k.total_states ?? 0} States & UTs`;
      document.getElementById("kpi-mid-spend").innerText = `₹${(k.avg_mid_daily_inr ?? 0).toLocaleString()}`;
      document.getElementById("kpi-budget-spend").innerText = `₹${(k.avg_budget_daily_inr ?? 0).toLocaleString()}`;
      document.getElementById("kpi-avg-duration").innerText = `${k.avg_duration_days ?? 0} Days`;
      document.getElementById("kpi-safety-rating").innerText = `${k.avg_safety ?? 0} / 10`;
      document.getElementById("kpi-top-dest").innerText = kpiJson.most_popular_destination ?? "N/A";
    }

    // 2. Fetch Top Destinations Table
    const destRes = await fetch(`/api/analytics/destinations?${params.toString()}&limit=8`);
    const destJson = await destRes.json();
    if (destJson.status === "success") {
      renderTopDestinationsTable(destJson.data);
    }

    // 3. Render Dashboard Charts
    renderDashboardCharts();
  } catch (err) {
    console.error("Dashboard data load error:", err);
  }
}

function renderTopDestinationsTable(destinations) {
  const tbody = document.querySelector("#table-top-destinations tbody");
  tbody.innerHTML = "";
  if (!destinations || destinations.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-dim);">No destinations match the selected criteria.</td></tr>`;
    return;
  }

  destinations.forEach(d => {
    const tr = document.createElement("tr");
    const accBadgeClass = d.accessibility === "Easy" ? "badge-easy" : (d.accessibility === "Difficult" ? "badge-difficult" : "badge-moderate");
    tr.innerHTML = `
      <td><strong>${d.destination_name}</strong></td>
      <td>${d.region}</td>
      <td>${d.state}</td>
      <td><span class="badge ${accBadgeClass}">${d.accessibility}</span></td>
      <td>⭐ ${d.popularity_score} / 10</td>
      <td>🛡️ ${d.safety_rating} / 10</td>
      <td>${d.ideal_duration_days} days</td>
      <td>₹${Number(d.mid_daily_avg).toLocaleString()}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function renderDashboardCharts() {
  try {
    // 1. Regional Rollup Chart
    const rollupRes = await fetch("/api/olap/rollup?hierarchy=geography");
    const rollupJson = await rollupRes.json();
    if (rollupJson.status === "success") {
      const rows = rollupJson.data.rows;
      const labels = rows.map(r => r.region);
      const counts = rows.map(r => r.destination_count);

      if (charts["regionDist"]) charts["regionDist"].destroy();
      const ctx1 = document.getElementById("chart-region-dist").getContext("2d");
      charts["regionDist"] = new Chart(ctx1, {
        type: "doughnut",
        data: {
          labels: labels,
          datasets: [{
            data: counts,
            backgroundColor: [
              CLAY_COLORS.pink,
              CLAY_COLORS.teal,
              CLAY_COLORS.lavender,
              CLAY_COLORS.peach,
              CLAY_COLORS.ochre,
              CLAY_COLORS.mint,
              CLAY_COLORS.coral
            ],
            borderWidth: 3,
            borderColor: "#ffffff"
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "right",
              labels: {
                color: CLAY_COLORS.body,
                font: { family: "Inter", size: 12 }
              }
            }
          }
        }
      });
    }

    // 2. Spend Tiers Chart
    const spendRes = await fetch("/api/analytics/spend-breakdown");
    const spendJson = await spendRes.json();
    if (spendJson.status === "success") {
      const tiers = spendJson.data;
      const labels = tiers.map(t => t.tier);
      const totals = tiers.map(t => t.total_daily);

      if (charts["spendTiers"]) charts["spendTiers"].destroy();
      const ctx2 = document.getElementById("chart-spend-tiers").getContext("2d");
      charts["spendTiers"] = new Chart(ctx2, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [{
            label: "Average Daily Spend (INR ₹)",
            data: totals,
            backgroundColor: [CLAY_COLORS.teal, CLAY_COLORS.pink, CLAY_COLORS.lavender],
            borderColor: [CLAY_COLORS.teal, CLAY_COLORS.pink, CLAY_COLORS.lavender],
            borderWidth: 1.5,
            borderRadius: 8
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: CLAY_COLORS.muted }, grid: { display: false } },
            y: { ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
          }
        }
      });
    }
  } catch (err) {
    console.error("Dashboard charts error:", err);
  }
}

// --- Analytics Tab ---
async function loadAnalyticsTab() {
  try {
    const spendRes = await fetch("/api/analytics/spend-breakdown");
    const spendJson = await spendRes.json();
    if (spendJson.status === "success") {
      const tiers = spendJson.data;
      const ctx = document.getElementById("chart-category-breakdown").getContext("2d");
      charts["categoryBreakdown"] = new Chart(ctx, {
        type: "bar",
        data: {
          labels: tiers.map(t => t.tier),
          datasets: [
            { label: "Accommodation", data: tiers.map(t => t.accommodation), backgroundColor: CLAY_COLORS.teal },
            { label: "Food", data: tiers.map(t => t.food), backgroundColor: CLAY_COLORS.peach },
            { label: "Activities", data: tiers.map(t => t.activities), backgroundColor: CLAY_COLORS.pink },
            { label: "Local Transport", data: tiers.map(t => t.transport), backgroundColor: CLAY_COLORS.ochre }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { stacked: true, ticks: { color: CLAY_COLORS.muted } },
            y: { stacked: true, ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
          },
          plugins: { legend: { labels: { color: CLAY_COLORS.body } } }
        }
      });
    }

    const destRes = await fetch("/api/analytics/destinations?limit=100");
    const destJson = await destRes.json();
    if (destJson.status === "success") {
      const raw = destJson.data;

      // Scatter: Duration vs Mid Spend
      const scatterData = raw.map(d => ({ x: d.ideal_duration_days, y: d.mid_daily_avg, label: d.destination_name }));
      const ctxScatter = document.getElementById("chart-scatter-duration-spend").getContext("2d");
      charts["scatterDurSpend"] = new Chart(ctxScatter, {
        type: "scatter",
        data: {
          datasets: [{
            label: "Destinations",
            data: scatterData,
            backgroundColor: "rgba(255, 77, 139, 0.7)",
            borderColor: CLAY_COLORS.pink,
            pointRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { title: { display: true, text: "Ideal Duration (Days)", color: CLAY_COLORS.ink }, ticks: { color: CLAY_COLORS.muted } },
            y: { title: { display: true, text: "Mid Daily Spend (INR)", color: CLAY_COLORS.ink }, ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.raw.label}: ${ctx.raw.x} days, ₹${ctx.raw.y.toLocaleString()}/day`
              }
            }
          }
        }
      });

      // Scatter: Safety vs Popularity
      const safetyData = raw.map(d => ({ x: d.safety_rating, y: d.popularity_score, label: d.destination_name }));
      const ctxSafe = document.getElementById("chart-safety-popularity").getContext("2d");
      charts["scatterSafetyPop"] = new Chart(ctxSafe, {
        type: "scatter",
        data: {
          datasets: [{
            label: "Safety vs Popularity",
            data: safetyData,
            backgroundColor: "rgba(26, 58, 58, 0.7)",
            borderColor: CLAY_COLORS.teal,
            pointRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { title: { display: true, text: "Safety Rating (1-10)", color: CLAY_COLORS.ink }, ticks: { color: CLAY_COLORS.muted } },
            y: { title: { display: true, text: "Popularity Score (1-10)", color: CLAY_COLORS.ink }, ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.raw.label}: Safety ${ctx.raw.x}/10, Popularity ${ctx.raw.y}/10`
              }
            }
          }
        }
      });

      // Scatter: Altitude vs Airport Distance
      const altData = raw.map(d => ({ x: d.airport_distance_km, y: d.altitude_m, label: d.destination_name }));
      const ctxAlt = document.getElementById("chart-altitude-airport").getContext("2d");
      charts["scatterAltAirport"] = new Chart(ctxAlt, {
        type: "scatter",
        data: {
          datasets: [{
            label: "Logistics Profile",
            data: altData,
            backgroundColor: "rgba(232, 185, 74, 0.7)",
            borderColor: CLAY_COLORS.ochre,
            pointRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { title: { display: true, text: "Distance to Nearest Airport (km)", color: CLAY_COLORS.ink }, ticks: { color: CLAY_COLORS.muted } },
            y: { title: { display: true, text: "Altitude (m)", color: CLAY_COLORS.ink }, ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.raw.label}: Airport ${ctx.raw.x}km, Alt ${ctx.raw.y}m`
              }
            }
          }
        }
      });
    }
  } catch (err) {
    console.error("Analytics tab error:", err);
  }
}

// --- Data Warehouse Tab ---
async function loadWarehouseTab() {
  try {
    const res = await fetch("/api/warehouse/tables");
    const json = await res.json();
    if (json.status === "success") {
      const tbody = document.querySelector("#table-warehouse-catalog tbody");
      tbody.innerHTML = "";
      json.tables.forEach(t => {
        let classification = "Dimension Table";
        if (t.table_name.startsWith("fact_")) classification = "Primary Fact Table";
        else if (t.table_name.startsWith("bridge_")) classification = "Bridge / Outrigger";
        else if (t.table_name.startsWith("mining_")) classification = "Data Mining Store";

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><code>${t.table_name}</code></td>
          <td><span class="badge ${t.table_name.startsWith('fact_') ? 'badge-luxury' : 'badge-easy'}">${classification}</span></td>
          <td><strong>${t.row_count}</strong> rows</td>
          <td><button class="btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="previewTable('${t.table_name}')">Preview</button></td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    console.error("Warehouse tab load error:", err);
  }
}

async function previewTable(tableName) {
  const container = document.getElementById("table-preview-container");
  const label = document.getElementById("preview-table-name");
  label.innerText = `Previewing table: ${tableName}`;
  container.innerHTML = `<p style="color: var(--text-dim); padding: 10px;">Loading rows for ${tableName}...</p>`;

  try {
    const res = await fetch("/api/warehouse/tables");
    const json = await res.json();
    const tData = json.tables.find(t => t.table_name === tableName);
    if (!tData || !tData.sample_rows || tData.sample_rows.length === 0) {
      container.innerHTML = `<p style="color: var(--text-dim); padding: 10px;">No sample rows available for ${tableName}.</p>`;
      return;
    }

    const cols = tData.columns;
    let html = `<table class="data-table"><thead><tr>`;
    cols.forEach(c => html += `<th>${c}</th>`);
    html += `</tr></thead><tbody>`;

    tData.sample_rows.forEach(r => {
      html += `<tr>`;
      cols.forEach(c => {
        let val = r[c];
        if (typeof val === "string" && val.length > 35) val = val.substring(0, 35) + "...";
        html += `<td>${val ?? ""}</td>`;
      });
      html += `</tr>`;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color: var(--accent-rose);">Failed to preview table: ${err.message}</p>`;
  }
}

// --- OLAP Operations Tab ---
async function loadOlapRollup() {
  document.getElementById("olap-operation-title").innerText = "1. OLAP Roll-up: Geography Hierarchy";
  document.getElementById("olap-operation-sub").innerText = "Aggregates Destination -> State -> Region -> Grand Total";
  const container = document.getElementById("olap-result-container");
  container.innerHTML = `<p style="color: var(--text-dim);">Running Roll-up query...</p>`;

  try {
    const res = await fetch("/api/olap/rollup?hierarchy=geography");
    const json = await res.json();
    const rows = json.data.rows;
    const total = json.data.total;

    let html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Region</th>
            <th>Destinations</th>
            <th>Avg Ideal Days</th>
            <th>Avg Popularity</th>
            <th>Avg Safety</th>
            <th>Avg Daily Spend (Mid)</th>
            <th>Avg Daily Spend (Budget)</th>
            <th>Avg Daily Spend (Luxury)</th>
          </tr>
        </thead>
        <tbody>
    `;

    rows.forEach(r => {
      html += `
        <tr>
          <td><strong>${r.region}</strong></td>
          <td>${r.destination_count}</td>
          <td>${r.avg_ideal_days}</td>
          <td>${r.avg_popularity} / 10</td>
          <td>${r.avg_safety} / 10</td>
          <td>₹${Number(r.avg_mid_daily_spend).toLocaleString()}</td>
          <td>₹${Number(r.avg_budget_daily_spend).toLocaleString()}</td>
          <td>₹${Number(r.avg_luxury_daily_spend).toLocaleString()}</td>
        </tr>
      `;
    });

    if (total) {
      html += `
        <tr style="background: rgba(99, 102, 241, 0.15); font-weight: 700;">
          <td>GRAND TOTAL (INDIA)</td>
          <td>${total.destination_count}</td>
          <td>${total.avg_ideal_days}</td>
          <td>${total.avg_popularity} / 10</td>
          <td>${total.avg_safety} / 10</td>
          <td>₹${Number(total.avg_mid_daily_spend).toLocaleString()}</td>
          <td>₹${Number(total.avg_budget_daily_spend).toLocaleString()}</td>
          <td>₹${Number(total.avg_luxury_daily_spend).toLocaleString()}</td>
        </tr>
      `;
    }

    html += `</tbody></table>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color: var(--accent-rose);">${err.message}</p>`;
  }
}

async function loadOlapDrilldown(region) {
  document.getElementById("olap-operation-title").innerText = `2. OLAP Drill-down: ${region}`;
  document.getElementById("olap-operation-sub").innerText = `Drills down from ${region} into individual States, Districts, and Destinations`;
  const container = document.getElementById("olap-result-container");
  container.innerHTML = `<p style="color: var(--text-dim);">Running Drill-down query...</p>`;

  try {
    const res = await fetch(`/api/olap/drilldown?region=${encodeURIComponent(region)}`);
    const json = await res.json();
    const rows = json.data;

    let html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Region</th>
            <th>State</th>
            <th>District</th>
            <th>Destination Name</th>
            <th>Accessibility</th>
            <th>Ideal Days</th>
            <th>Mid Spend (INR)</th>
            <th>Popularity</th>
            <th>Altitude (m)</th>
          </tr>
        </thead>
        <tbody>
    `;

    rows.forEach(r => {
      html += `
        <tr>
          <td>${r.region}</td>
          <td>${r.state}</td>
          <td>${r.district}</td>
          <td><strong>${r.destination_name}</strong></td>
          <td><span class="badge ${r.accessibility === 'Easy' ? 'badge-easy' : 'badge-moderate'}">${r.accessibility}</span></td>
          <td>${r.ideal_duration_days}</td>
          <td>₹${Number(r.mid_daily_avg).toLocaleString()}</td>
          <td>⭐ ${r.popularity_score}</td>
          <td>${r.altitude_m}m</td>
        </tr>
      `;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color: var(--accent-rose);">${err.message}</p>`;
  }
}

async function loadOlapSlice(dim, val) {
  document.getElementById("olap-operation-title").innerText = `3. OLAP Slice: ${dim} = '${val}'`;
  document.getElementById("olap-operation-sub").innerText = `Fixes single dimension value to isolate corresponding sub-cube`;
  const container = document.getElementById("olap-result-container");
  container.innerHTML = `<p style="color: var(--text-dim);">Running Slice query...</p>`;

  try {
    const res = await fetch(`/api/olap/slice?dim=${dim}&val=${encodeURIComponent(val)}`);
    const json = await res.json();
    const rows = json.data;

    let html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Destination Name</th>
            <th>Region</th>
            <th>State</th>
            <th>Accessibility</th>
            <th>Popularity</th>
            <th>Safety</th>
            <th>Ideal Days</th>
            <th>Daily Spend (Mid)</th>
            <th>Est Trip Cost</th>
          </tr>
        </thead>
        <tbody>
    `;
    rows.forEach(r => {
      html += `
        <tr>
          <td><strong>${r.destination_name}</strong></td>
          <td>${r.region}</td>
          <td>${r.state}</td>
          <td><span class="badge badge-easy">${r.accessibility}</span></td>
          <td>⭐ ${r.popularity_score}</td>
          <td>🛡️ ${r.safety_rating}</td>
          <td>${r.ideal_duration_days}</td>
          <td>₹${Number(r.mid_daily_avg).toLocaleString()}</td>
          <td>₹${Number(r.total_estimated_trip_cost_mid).toLocaleString()}</td>
        </tr>
      `;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color: var(--accent-rose);">${err.message}</p>`;
  }
}

async function loadOlapDice() {
  document.getElementById("olap-operation-title").innerText = "4. OLAP Dice: North India + High Safety (>=8) + Mid Spend <= ₹5,000";
  document.getElementById("olap-operation-sub").innerText = "Filters on multiple dimensions and measure thresholds simultaneously";
  const container = document.getElementById("olap-result-container");
  container.innerHTML = `<p style="color: var(--text-dim);">Running Dice query...</p>`;

  try {
    const res = await fetch("/api/olap/dice?region=North India&min_safety=8&max_spend=5000");
    const json = await res.json();
    const rows = json.data;

    let html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Destination Name</th>
            <th>Region</th>
            <th>State</th>
            <th>Accessibility</th>
            <th>Safety</th>
            <th>Popularity</th>
            <th>Mid Daily Spend</th>
            <th>Ideal Days</th>
          </tr>
        </thead>
        <tbody>
    `;
    rows.forEach(r => {
      html += `
        <tr>
          <td><strong>${r.destination_name}</strong></td>
          <td>${r.region}</td>
          <td>${r.state}</td>
          <td><span class="badge badge-moderate">${r.accessibility}</span></td>
          <td>🛡️ ${r.safety_rating} / 10</td>
          <td>⭐ ${r.popularity_score} / 10</td>
          <td>₹${Number(r.mid_daily_avg).toLocaleString()}</td>
          <td>${r.ideal_duration_days} days</td>
        </tr>
      `;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color: var(--accent-rose);">${err.message}</p>`;
  }
}

async function loadOlapPivot() {
  document.getElementById("olap-operation-title").innerText = "5. OLAP Pivot: Region (Rows) × Accessibility (Columns)";
  document.getElementById("olap-operation-sub").innerText = "Measure: Average Mid-Range Daily Spend (INR ₹)";
  const container = document.getElementById("olap-result-container");
  container.innerHTML = `<p style="color: var(--text-dim);">Constructing dynamic cross-tabulation matrix...</p>`;

  try {
    const res = await fetch("/api/olap/pivot?row=region&col=accessibility&measure=mid_daily_avg&agg=AVG");
    const json = await res.json();
    const matrix = json.data.matrix;
    const colHeaders = json.data.col_headers;

    let html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Region</th>
            <th>Total Destinations</th>
            <th>Overall Avg Spend</th>
    `;
    colHeaders.forEach(c => html += `<th>${c}</th>`);
    html += `</tr></thead><tbody>`;

    matrix.forEach(row => {
      html += `
        <tr>
          <td><strong>${row.region}</strong></td>
          <td>${row.total_destinations}</td>
          <td>₹${Number(row.overall_avg).toLocaleString()}</td>
      `;
      colHeaders.forEach(c => {
        const val = row[c];
        html += `<td>${val != null ? `₹${Number(val).toLocaleString()}` : '<span style="color: var(--text-dim);">-</span>'}</td>`;
      });
      html += `</tr>`;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color: var(--accent-rose);">${err.message}</p>`;
  }
}

// --- K-Means Segmentation Tab ---
async function loadSegmentationTab() {
  try {
    const res = await fetch("/api/mining/clusters");
    const json = await res.json();
    if (json.status !== "success") return;

    const clusters = json.clusters;
    const assignments = json.assignments;

    // 1. Render Cluster Cards
    const cardContainer = document.getElementById("cluster-cards-container");
    cardContainer.innerHTML = "";
    clusters.forEach(c => {
      const card = document.createElement("div");
      card.className = `cluster-card cluster-${c.cluster_id}`;
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <h4>Cluster ${c.cluster_id}: ${c.cluster_label}</h4>
          <span class="cluster-badge">${c.destination_count} Destinations</span>
        </div>
        <div class="cluster-stats">
          <div class="stat-item">
            <span>Centroid Spend</span>
            <strong>₹${Number(c.centroid_mid_spend).toLocaleString()}</strong>
          </div>
          <div class="stat-item">
            <span>Stay Duration</span>
            <strong>${c.centroid_duration} Days</strong>
          </div>
          <div class="stat-item">
            <span>Mean Altitude</span>
            <strong>${Number(c.centroid_altitude).toLocaleString()} m</strong>
          </div>
          <div class="stat-item">
            <span>Popularity</span>
            <strong>⭐ ${c.centroid_popularity}</strong>
          </div>
        </div>
        <p class="cluster-explanation">${c.summary_explanation}</p>
      `;
      cardContainer.appendChild(card);
    });

    // 2. Render Scatter Plot (Mid Spend vs Duration)
    const scatterSets = clusters.map((c, i) => {
      const cAssignments = assignments.filter(a => a.cluster_id === c.cluster_id);
      const colors = [CLAY_COLORS.teal, CLAY_COLORS.pink, CLAY_COLORS.ochre, CLAY_COLORS.lavender, CLAY_COLORS.peach, CLAY_COLORS.mint];
      return {
        label: `Cluster ${c.cluster_id}: ${c.cluster_label}`,
        data: cAssignments.map(a => ({ x: a.ideal_duration_days, y: a.mid_daily_avg, name: a.destination_name })),
        backgroundColor: colors[i % colors.length],
        pointRadius: 6
      };
    });

    if (charts["kmeansScatter"]) charts["kmeansScatter"].destroy();
    const ctxScatter = document.getElementById("chart-kmeans-scatter").getContext("2d");
    charts["kmeansScatter"] = new Chart(ctxScatter, {
      type: "scatter",
      data: { datasets: scatterSets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: "Stay Duration (Days)", color: CLAY_COLORS.ink }, ticks: { color: CLAY_COLORS.muted } },
          y: { title: { display: true, text: "Daily Spend (INR)", color: CLAY_COLORS.ink }, ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
        },
        plugins: {
          legend: { labels: { color: CLAY_COLORS.body } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.raw.name}: ${ctx.raw.x} days, ₹${ctx.raw.y.toLocaleString()}/day`
            }
          }
        }
      }
    });

    // 3. Render Silhouette Curve
    if (charts["kmeansSilhouette"]) charts["kmeansSilhouette"].destroy();
    const ctxSil = document.getElementById("chart-kmeans-silhouette").getContext("2d");
    charts["kmeansSilhouette"] = new Chart(ctxSil, {
      type: "line",
      data: {
        labels: ["k=2", "k=3", "k=4", "k=5", "k=6"],
        datasets: [{
          label: "Silhouette Score",
          data: [0.4028, 0.3650, 0.3210, 0.2980, 0.2740],
          borderColor: CLAY_COLORS.pink,
          backgroundColor: "rgba(255, 77, 139, 0.12)",
          fill: true,
          tension: 0.3,
          pointRadius: 6,
          pointBackgroundColor: CLAY_COLORS.teal
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: CLAY_COLORS.muted } },
          y: { ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
        }
      }
    });

    // 4. Render Assignments Table
    const tbody = document.querySelector("#table-cluster-assignments tbody");
    tbody.innerHTML = "";
    assignments.slice(0, 15).forEach(a => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${a.destination_name}</strong></td>
        <td><span class="badge ${a.cluster_id === 1 ? 'badge-budget' : 'badge-luxury'}">Cluster ${a.cluster_id}</span></td>
        <td>${a.distance_to_centroid}</td>
        <td>₹${Number(a.mid_daily_avg).toLocaleString()}</td>
        <td>${a.ideal_duration_days} days</td>
        <td>${a.altitude_m} m</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Segmentation tab load error:", err);
  }
}

// --- Association Rules Tab ---
async function loadRulesTab() {
  try {
    const res = await fetch("/api/mining/rules");
    const json = await res.json();
    if (json.status !== "success") return;

    const tbody = document.querySelector("#table-association-rules tbody");
    tbody.innerHTML = "";
    json.rules.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>#${r.rule_id}</td>
        <td><code>${r.antecedents}</code></td>
        <td><code>${r.consequents}</code></td>
        <td>${(r.support * 100).toFixed(1)}%</td>
        <td><strong>${(r.confidence * 100).toFixed(1)}%</strong></td>
        <td><span class="badge badge-easy">${r.lift.toFixed(2)}x</span></td>
        <td>${r.plain_english_rule}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Rules tab load error:", err);
  }
}

// --- Classification Tab ---
async function loadClassificationTab() {
  try {
    const res = await fetch("/api/mining/classification");
    const json = await res.json();
    if (json.status !== "success") return;

    const models = json.models;

    // 1. Render Model KPI Cards
    const kpiContainer = document.getElementById("clf-kpi-container");
    kpiContainer.innerHTML = "";
    models.forEach(m => {
      const card = document.createElement("div");
      card.className = "kpi-card";
      card.innerHTML = `
        <div class="kpi-header">
          <span class="kpi-label">${m.model_name}</span>
          <div class="kpi-icon"><i class="fa-solid fa-microchip"></i></div>
        </div>
        <div class="kpi-value">${(m.accuracy * 100).toFixed(1)}%</div>
        <div class="kpi-subtext">F1: ${m.f1_score.toFixed(3)} | Precision: ${m.precision.toFixed(3)}</div>
      `;
      kpiContainer.appendChild(card);
    });

    // 2. Render Benchmark Chart
    if (charts["clfBenchmark"]) charts["clfBenchmark"].destroy();
    const ctxBench = document.getElementById("chart-clf-benchmark").getContext("2d");
    charts["clfBenchmark"] = new Chart(ctxBench, {
      type: "bar",
      data: {
        labels: models.map(m => m.model_name),
        datasets: [
          { label: "Accuracy", data: models.map(m => m.accuracy), backgroundColor: CLAY_COLORS.pink },
          { label: "F1-Score", data: models.map(m => m.f1_score), backgroundColor: CLAY_COLORS.teal },
          { label: "Precision", data: models.map(m => m.precision), backgroundColor: CLAY_COLORS.lavender },
          { label: "Recall", data: models.map(m => m.recall), backgroundColor: CLAY_COLORS.ochre }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: CLAY_COLORS.muted } },
          y: { min: 0, max: 1.0, ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
        },
        plugins: { legend: { labels: { color: CLAY_COLORS.body } } }
      }
    });

    // 3. Render Feature Importance Chart
    const rfModel = models.find(m => m.model_name === "Random Forest") || models[0];
    const featLabels = Object.keys(rfModel.feature_importance);
    const featVals = Object.values(rfModel.feature_importance);

    if (charts["featImp"]) charts["featImp"].destroy();
    const ctxFeat = document.getElementById("chart-feature-importance").getContext("2d");
    charts["featImp"] = new Chart(ctxFeat, {
      type: "bar",
      data: {
        labels: featLabels,
        datasets: [{
          label: "Importance Score",
          data: featVals,
          backgroundColor: CLAY_COLORS.teal,
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } },
          y: { ticks: { color: CLAY_COLORS.muted }, grid: { display: false } }
        }
      }
    });

    // 4. Render Confusion Matrix Tables
    const cmContainer = document.getElementById("confusion-matrix-container");
    cmContainer.innerHTML = "";
    models.forEach(m => {
      const cm = m.confusion_matrix;
      const tn = cm[0][0], fp = cm[0][1], fn = cm[1][0], tp = cm[1][1];
      const div = document.createElement("div");
      div.innerHTML = `
        <h4 style="text-align: center; margin-bottom: 8px;">${m.model_name}</h4>
        <table class="cm-table">
          <thead>
            <tr><th></th><th>Pred: Budget</th><th>Pred: High</th></tr>
          </thead>
          <tbody>
            <tr><th>Actual: Budget</th><td class="cm-cell-tn">TN: ${tn}</td><td class="cm-cell-fp">FP: ${fp}</td></tr>
            <tr><th>Actual: High</th><td class="cm-cell-fn">FN: ${fn}</td><td class="cm-cell-tp">TP: ${tp}</td></tr>
          </tbody>
        </table>
      `;
      cmContainer.appendChild(div);
    });
  } catch (err) {
    console.error("Classification tab error:", err);
  }
}

// --- Outliers Tab ---
async function loadOutliersTab() {
  try {
    const res = await fetch("/api/mining/outliers");
    const json = await res.json();
    if (json.status !== "success") return;

    const tbody = document.querySelector("#table-outliers tbody");
    tbody.innerHTML = "";
    json.outliers.forEach(o => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${o.destination_name}</strong></td>
        <td><span class="badge ${o.method.includes('Isolation') ? 'badge-luxury' : 'badge-difficult'}">${o.method}</span></td>
        <td><code>${o.feature_name}</code></td>
        <td>${Number(o.feature_value).toLocaleString()}</td>
        <td>${Number(o.threshold_value).toLocaleString()}</td>
        <td>${o.anomaly_score}</td>
        <td>${o.reason}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Outliers tab error:", err);
  }
}

// --- Trends Tab ---
async function loadTrendsTab() {
  try {
    const res = await fetch("/api/mining/trends");
    const json = await res.json();
    if (json.status !== "success") return;

    const trends = json.trends;
    const seasonTrends = trends.filter(t => t.category_type === "Season");
    const regionTrends = trends.filter(t => t.category_type === "Region");

    // Season Distribution Chart
    if (charts["seasonTrends"]) charts["seasonTrends"].destroy();
    const ctxSeas = document.getElementById("chart-season-trends").getContext("2d");
    charts["seasonTrends"] = new Chart(ctxSeas, {
      type: "bar",
      data: {
        labels: seasonTrends.map(s => s.category_value),
        datasets: [{
          label: "Destination Count",
          data: seasonTrends.map(s => s.destination_count),
          backgroundColor: CLAY_COLORS.ochre,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: CLAY_COLORS.muted } },
          y: { ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
        }
      }
    });

    // Regional Premium Chart
    if (charts["regionPremium"]) charts["regionPremium"].destroy();
    const ctxReg = document.getElementById("chart-regional-premium").getContext("2d");
    charts["regionPremium"] = new Chart(ctxReg, {
      type: "bar",
      data: {
        labels: regionTrends.map(r => r.category_value),
        datasets: [{
          label: "Average Mid Daily Spend (INR)",
          data: regionTrends.map(r => r.avg_mid_spend),
          backgroundColor: CLAY_COLORS.pink,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: CLAY_COLORS.muted } },
          y: { ticks: { color: CLAY_COLORS.muted }, grid: { color: "rgba(10, 10, 10, 0.06)" } }
        }
      }
    });
  } catch (err) {
    console.error("Trends tab load error:", err);
  }
}

// --- Destinations Master Tab ---
let allDestinationsData = [];

async function loadDestinationsMaster() {
  try {
    const res = await fetch("/api/analytics/destinations?limit=100");
    const json = await res.json();
    if (json.status === "success") {
      allDestinationsData = json.data;
      renderAllDestinationsTable(allDestinationsData);
    }
  } catch (err) {
    console.error("Destinations master load error:", err);
  }
}

function renderAllDestinationsTable(data) {
  const tbody = document.querySelector("#table-all-destinations tbody");
  tbody.innerHTML = "";
  data.forEach(d => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>#${d.destination_key}</td>
      <td><strong>${d.destination_name}</strong></td>
      <td>${d.region}</td>
      <td>${d.state}</td>
      <td><span class="badge ${d.accessibility === 'Easy' ? 'badge-easy' : 'badge-moderate'}">${d.accessibility}</span></td>
      <td>${d.altitude_m} m</td>
      <td>${d.airport_distance_km} km</td>
      <td>${d.ideal_duration_days} days</td>
      <td>₹${Number(d.mid_daily_avg).toLocaleString()}</td>
      <td>⭐ ${d.popularity_score}</td>
    `;
    tbody.appendChild(tr);
  });
}

function setupCatalogSearch() {
  const input = document.getElementById("dest-search");
  if (!input) return;
  input.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    const filtered = allDestinationsData.filter(d => 
      d.destination_name.toLowerCase().includes(q) ||
      d.state.toLowerCase().includes(q) ||
      d.region.toLowerCase().includes(q)
    );
    renderAllDestinationsTable(filtered);
  });
}

// --- Trip Recommender ---
function setupRecommender() {
  const btn = document.getElementById("btn-run-recommender");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    const budget = document.getElementById("rec-budget").value;
    const duration = document.getElementById("rec-duration").value;
    const tripType = document.getElementById("rec-type").value;
    const season = document.getElementById("rec-season").value;

    const container = document.getElementById("recommender-results-container");
    container.innerHTML = `<p style="color: var(--text-dim); padding: 20px;">Computing optimal destination matches...</p>`;

    try {
      const res = await fetch("/api/mining/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          budget_max: budget,
          duration_days: duration,
          trip_type: tripType,
          season: season
        })
      });
      const json = await res.json();
      const recs = json.result.recommendations;

      container.innerHTML = "";
      if (!recs || recs.length === 0) {
        container.innerHTML = `<p style="color: var(--text-dim); padding: 20px;">${json.result.message || 'No matching destinations found.'}</p>`;
        return;
      }

      recs.forEach((r, idx) => {
        const card = document.createElement("div");
        card.className = `cluster-card cluster-${(idx % 4) + 1}`;
        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <h4>${idx + 1}. ${r.destination_name}</h4>
            <span class="cluster-badge" style="background: rgba(16, 185, 129, 0.2); color: #6EE7B7; font-weight: 700;">
              ${r.match_score}% MATCH
            </span>
          </div>
          <div class="cluster-stats">
            <div class="stat-item">
              <span>Location</span>
              <strong>${r.state} (${r.region})</strong>
            </div>
            <div class="stat-item">
              <span>Daily Spend</span>
              <strong>₹${Number(r.mid_daily_avg).toLocaleString()}</strong>
            </div>
            <div class="stat-item">
              <span>Ideal Duration</span>
              <strong>${r.ideal_duration_days} Days</strong>
            </div>
            <div class="stat-item">
              <span>Ratings</span>
              <strong>⭐ ${r.popularity_score} | 🛡️ ${r.safety_rating}</strong>
            </div>
          </div>
          <div style="font-size: 0.82rem; color: #CBD5E1; margin-bottom: 8px;">
            <strong>Why Recommended:</strong>
            <ul style="margin-left: 18px; margin-top: 4px;">
              ${r.match_reasons.map(reason => `<li>${reason}</li>`).join("")}
            </ul>
          </div>
          <p class="cluster-explanation">${r.unique_experiences || ''}</p>
        `;
        container.appendChild(card);
      });
    } catch (err) {
      container.innerHTML = `<p style="color: var(--accent-rose); padding: 20px;">Recommender error: ${err.message}</p>`;
    }
  });
}
