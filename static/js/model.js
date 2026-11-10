// Housing Price Model page
let cvType = "simple";
const LAYOUT = {
  font: { family: "Inter, system-ui, sans-serif", size: 12, color: "#17212b" },
  margin: { l: 50, r: 10, t: 40, b: 40 }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", height: 340,
};
const CONFIG = { displaylogo: false, responsive: true, displayModeBar: false };
const pp = v => fmt.dec(v * 100, 2) + " pp";

function bars(el, title, rows, key, best, format, zeroLine) {
  const ys = rows.map(r => key === "mae" ? r[key] * 100 : r[key]);
  const lo = Math.min(0, ...ys), hi = Math.max(0, ...ys), pad = (hi - lo) * 0.18;
  const width = document.getElementById(el).getBoundingClientRect().width;
  Plotly.newPlot(el, [{
    type: "bar", x: rows.map(r => r.model.replace(" Regression", "<br>Regression")), y: ys,
    marker: { color: rows.map(r => r.model === best ? "#0f6e8c" : "#a9cfdc") },
    text: rows.map(r => format(r[key])), textposition: "outside", cliponaxis: false,
    hovertemplate: "%{x}: %{text}<extra></extra>",
  }], { ...LAYOUT, width: width || undefined, title: { text: title, font: { size: 14 } },
        xaxis: { automargin: true, tickfont: { size: 11 } },
        yaxis: { gridcolor: "#e2e7ec", zeroline: zeroLine, zerolinecolor: "#17212b", ticksuffix: key === "mae" ? " pp" : "",
                 range: [lo - (lo < 0 ? pad : 0), hi + pad], automargin: true } }, CONFIG);
}

function render(d) {
  // Show the results area first: Plotly measures the container width when drawing,
  // and a hidden container has no width (charts would get a fixed default size).
  document.getElementById("results").classList.remove("hidden");
  const rows = d.results;
  document.getElementById("cv-label").textContent = (d.cv_type === "nested" ? "Nested" : "Simple") + " 5-fold cross-validation on " + d.n_train + " training rows";
  bars("chart-r2", "Average R² (higher is better)", rows, "r2", d.best_model, v => fmt.dec(v, 2), true);
  bars("chart-mae", "Average error, MAE (lower is better)", rows, "mae", d.best_model, pp, false);
  document.getElementById("table").innerHTML =
    "<tr><th>Model</th><th>Avg. R²</th><th>Avg. MAE</th></tr>" +
    rows.map(r => `<tr class="${r.model === d.best_model ? "best" : ""}"><td>${r.model}${r.model === d.best_model ? " (best)" : ""}</td><td>${fmt.dec(r.r2, 3)}</td><td>${pp(r.mae)}</td></tr>`).join("");

  const t = d.test;
  const gain = (1 - t.mae / t.baseline_mae) * 100;
  document.getElementById("test-intro").textContent =
    `${d.best_model} was retrained on all ${d.n_train} training rows and then predicted the ${d.n_test} rows it had never seen.`;
  document.getElementById("test-kpis").innerHTML = [
    ["R² on test set", fmt.dec(t.r2, 2), "share of variation explained"],
    ["Average error (MAE)", pp(t.mae), `RMSE ${pp(t.rmse)}`],
    ["Naive guess", pp(t.baseline_mae), "error when always predicting the average"],
  ].map(([l, n, s]) => `<div class="kpi"><div class="lbl">${l}</div><div class="num">${n}</div><div class="sub">${s}</div></div>`).join("");

  const negatives = rows.filter(r => r.r2 < 0).map(r => r.model);
  let text = `<strong>How to read this:</strong> on unseen data the ${d.best_model} is off by ${pp(t.mae)} on average, `
    + (gain > 0 ? `about ${fmt.dec(gain, 0)} % less than a naive guess. ` : `which is not better than a naive guess. `);
  const list = negatives.length > 1 ? negatives.slice(0, -1).join(", ") + " and " + negatives.at(-1) : negatives[0];
  if (negatives.length) text += `${list} ${negatives.length > 1 ? "have" : "has"} a negative R² – ${negatives.length > 1 ? "they predict" : "it predicts"} worse than the average, a sign that the relationships in the data are weak and that ${d.n_train} training rows are few for ${d.n_features} features. `;
  text += "The models find patterns, not causes: a good fit would not prove that short-term rentals drive house prices.";
  document.getElementById("verdict").innerHTML = text;
  requestAnimationFrame(() => fitCharts(["chart-r2", "chart-mae"]));
}

// Keep charts fitted to their cards when the window size changes
function fitCharts(ids) {
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el.data) Plotly.relayout(el, { width: el.getBoundingClientRect().width });
  });
}
window.addEventListener("resize", () => fitCharts(["chart-r2", "chart-mae"]));

document.querySelectorAll("#cv button").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll("#cv button").forEach(b => b.classList.toggle("active", b === btn));
  cvType = btn.dataset.value;
}));

document.getElementById("run").addEventListener("click", async () => {
  const button = document.getElementById("run"), running = document.getElementById("running");
  button.disabled = true; running.classList.remove("hidden");
  try {
    render(await fetch(`/api/model?cv=${cvType}`).then(r => r.json()));
  } finally {
    button.disabled = false; running.classList.add("hidden");
  }
});
