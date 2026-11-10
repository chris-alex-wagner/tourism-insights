// Country Insights page
const state = { country: null, year: null, level: 1, indicator: "guest_nights" };
const COLORS = ["#0f6e8c", "#e07a2e", "#6a8d3a"];
const SCALE = [[0, "#eef6f9"], [0.5, "#5ea9c2"], [1, "#0b4a66"]];
const LAYOUT = {
  font: { family: "Inter, system-ui, sans-serif", size: 12, color: "#17212b" },
  margin: { l: 10, r: 10, t: 40, b: 40 }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
};
const CONFIG = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d"] };

function kpi(label, num, sub = "") {
  return `<div class="kpi"><div class="lbl">${label}</div><div class="num">${num}</div><div class="sub">${sub}</div></div>`;
}

function drawKpis(d) {
  const s = d.stats;
  document.getElementById("kpi-title").textContent = `· ${d.name}, ${state.year}`;
  document.getElementById("kpis").innerHTML = [
    kpi(`Stays in ${state.year}`, fmt.int(s.stays_year), `${fmt.compact(s.stays_all_years)} stays in total 2018–2024`),
    kpi("Foreign guests", s.share_foreign == null ? "–" : fmt.dec(s.share_foreign) + " %", "share of all stays"),
    kpi("Peak month", s.peak_month || "–", s.peak_month_stays ? `${fmt.int(s.peak_month_stays)} stays` : ""),
    kpi("Average length of stay", s.avg_length.TOTAL == null ? "–" : fmt.dec(s.avg_length.TOTAL, 1) + " nights", "all guests"),
    kpi("… domestic vs. foreign", `${fmt.dec(s.avg_length.DOM, 1)} / ${fmt.dec(s.avg_length.FOR, 1)}`, "nights per stay"),
    kpi("Longest stays", s.longest_region || "–", s.longest_region_value ? `${fmt.dec(s.longest_region_value, 1)} nights per stay` : ""),
  ].join("");
}

function heatmap(el, title, h, z, unit) {
  const height = Math.max(320, 70 + h.regions.length * 26);
  Plotly.react(el, [{
    type: "heatmap", z, x: h.months.map(m => m.slice(0, 3)), y: h.regions, colorscale: SCALE, hoverongaps: false,
    hovertemplate: "<b>%{y}</b><br>%{x}: %{z:,.0f} " + unit + "<extra></extra>", colorbar: { thickness: 10, outlinewidth: 0 },
  }], { ...LAYOUT, title: { text: title, font: { size: 14 } }, height, margin: { ...LAYOUT.margin, l: 150 }, yaxis: { autorange: "reversed", automargin: true } }, CONFIG);
}

function trend(el, title, months, series, unit) {
  Plotly.react(el, series.map((s, i) => ({
    type: "scatter", mode: "lines+markers", name: s.name, x: months.map(m => m.slice(0, 3)), y: s.values,
    line: { color: COLORS[i], width: 2.5 }, marker: { size: 5 },
    hovertemplate: "%{x}: %{y:,.0f} " + unit + "<extra>" + s.name + "</extra>",
  })), { ...LAYOUT, title: { text: title, font: { size: 14 } }, height: 360, margin: { ...LAYOUT.margin, l: 60 },
        legend: { orientation: "h", y: -0.18 }, yaxis: { gridcolor: "#e2e7ec", rangemode: "tozero" }, hovermode: "x unified" }, CONFIG);
}

let requestId = 0;
async function update() {
  const id = ++requestId;
  const d = await fetch(`/api/country/${state.country}?year=${state.year}&level=${state.level}&indicator=${state.indicator}`).then(r => r.json());
  if (id !== requestId) return;
  drawKpis(d);
  const ind = d.indicator, h = d.heatmap;
  const sub = `${ind.label} · ${d.name} · ${state.year}`;
  document.getElementById("heat-sub").textContent = sub;
  document.getElementById("trend-sub").textContent = sub;

  const note = state.level === 2 && h.regions.some(r => r.endsWith("¹"))
    ? "¹ This region is not subdivided further: at NUTS 2 it is identical to its NUTS 1 region (e.g. the German city states and several smaller federal states)." : "";
  document.getElementById("footnote-heat").textContent = note;
  document.getElementById("footnote-trend").textContent = note && [...d.trend.DOM, ...d.trend.FOR].some(s => s.name.endsWith("¹")) ? note : "";
  const single = h.regions.length < 2;
  document.getElementById("no-regions").classList.toggle("hidden", !single);
  document.getElementById("heatmaps").classList.toggle("hidden", single);
  if (!single) {
    heatmap("heat-dom", "Domestic guests", h, h.DOM, ind.unit);
    heatmap("heat-for", "Foreign guests", h, h.FOR, ind.unit);
  }
  trend("trend-dom", "Domestic guests", d.trend.months, d.trend.DOM, ind.unit);
  trend("trend-for", "Foreign guests", d.trend.months, d.trend.FOR, ind.unit);
  requestAnimationFrame(fitAll);
}

const CHART_IDS = ["heat-dom", "heat-for", "trend-dom", "trend-for"];
function fitAll() {
  CHART_IDS.forEach(id => {
    const el = document.getElementById(id);
    const w = el.getBoundingClientRect().width;
    if (el.data && w) Plotly.relayout(el, { width: w });
  });
}
window.addEventListener("resize", fitAll);

document.querySelectorAll("#level button").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll("#level button").forEach(b => b.classList.toggle("active", b === btn));
  state.level = Number(btn.dataset.value);
  update();
}));
for (const id of ["country", "year", "indicator"]) {
  const el = document.getElementById(id);
  state[id] = id === "year" ? Number(el.value) : el.value;
  el.addEventListener("change", () => { state[id] = id === "year" ? Number(el.value) : el.value; update(); });
}
update();
