// Explore page: choropleth map (Leaflet) + Top 10 ranking
const PALETTE = ["#e6f2f6", "#c4e1ea", "#97c8d8", "#66abc3", "#3b8cab", "#1d6d8e", "#0b4a66"];
const NO_DATA = "#dfe3e7";
const GEO_FILES = { 0: "/static/geo/nuts0.json", 2: "/static/geo/nuts2.json" };

const state = { level: 0, indicator: "stays", resid: "TOTAL", year: null, month: 0 };
const geoCache = {};
let layer = null, legend = null, values = {}, breaks = [];

const map = L.map("map", { zoomSnap: 0.25, minZoom: 3, maxZoom: 9 }).setView([52, 12], 3.75);
map.attributionControl.addAttribution("Boundaries: &copy; EuroGeographics / Eurostat GISCO");

function status(msg) {
  const el = document.getElementById("map-status");
  el.textContent = msg || "";
  el.style.display = msg ? "block" : "none";
}

async function loadGeo(level) {
  if (!geoCache[level]) geoCache[level] = (await fetch(GEO_FILES[level])).json();
  return geoCache[level];
}

// Quantile class breaks: each colour holds roughly the same number of regions
function quantileBreaks(vals, n) {
  const s = [...vals].sort((a, b) => a - b);
  const b = [];
  for (let i = 1; i < n; i++) b.push(s[Math.floor((i / n) * (s.length - 1))]);
  return [...new Set(b)];
}
function colorFor(v) {
  if (v == null) return NO_DATA;
  let i = 0;
  while (i < breaks.length && v > breaks[i]) i++;
  return PALETTE[Math.round(i * (PALETTE.length - 1) / Math.max(breaks.length, 1))];
}

function periodLabel() {
  return (state.month ? MONTHS[state.month - 1] + " " : "") + state.year;
}

function drawLegend() {
  if (legend) legend.remove();
  const ind = INDICATORS[state.indicator];
  legend = L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "legend");
    const sorted = Object.values(values).sort((a, b) => a - b);
    const edges = [sorted[0], ...breaks, sorted[sorted.length - 1]];
    let html = `<div class="title">${ind.label}<br><span class="muted">${ind.unit}</span></div>`;
    for (let i = edges.length - 2; i >= 0; i--) {
      html += `<div class="row"><span class="sw" style="background:${colorFor(edges[i + 1])}"></span>${fmt.short(edges[i], state.indicator)} – ${fmt.short(edges[i + 1], state.indicator)}</div>`;
    }
    html += `<div class="row"><span class="sw" style="background:${NO_DATA}"></span>No data</div>`;
    div.innerHTML = html;
    return div;
  };
  legend.addTo(map);
}

function drawRanking(items) {
  const ind = INDICATORS[state.indicator];
  document.getElementById("ranking-title").textContent = `Top 10 ${state.level === 0 ? "countries" : "regions"}`;
  document.getElementById("ranking-sub").textContent = `${ind.label} · ${document.querySelector("#resid option:checked").textContent} · ${periodLabel()}`;
  const top = items.slice(0, 10);
  const max = top.length ? top[0].value : 1;
  document.getElementById("ranking").innerHTML = top.map((d, i) => `
    <li data-geo="${d.geo}">
      <div class="row1"><span><span class="rank">${i + 1}</span><span class="name">${d.name}</span></span>
      <span class="val">${fmt.value(d.value, state.indicator)}</span></div>
      <div class="bar" style="width:calc((100% - 22px) * ${d.value / max})"></div>
    </li>`).join("") || '<li class="muted">No data for this selection.</li>';
  document.querySelectorAll("#ranking li[data-geo]").forEach(li => li.addEventListener("click", () => focusRegion(li.dataset.geo)));
}

function focusRegion(geo) {
  if (!layer) return;
  layer.eachLayer(l => {
    if (l.feature.properties.id === geo) {
      map.fitBounds(l.getBounds(), { maxZoom: state.level === 0 ? 5 : 7, padding: [30, 30] });
      l.openTooltip();
    }
  });
}

let requestId = 0;
async function update() {
  const id = ++requestId;
  status("Loading …");
  document.getElementById("indicator-help").innerHTML = `<strong>${INDICATORS[state.indicator].label}:</strong> ${INDICATORS[state.indicator].help}`;
  const params = new URLSearchParams(state);
  const [geo, res] = await Promise.all([loadGeo(state.level), fetch(`/api/explore?${params}`).then(r => r.json())]);
  if (id !== requestId) return;
  values = Object.fromEntries(res.items.map(d => [d.geo, d.value]));
  const rank = Object.fromEntries(res.items.map((d, i) => [d.geo, i + 1]));
  breaks = res.items.length ? quantileBreaks(Object.values(values), PALETTE.length) : [];

  if (layer) layer.remove();
  layer = L.geoJSON(geo, {
    style: f => ({ fillColor: colorFor(values[f.properties.id]), fillOpacity: 0.85, color: "#ffffff", weight: state.level === 0 ? 1 : 0.6 }),
    onEachFeature: (f, l) => {
      const id = f.properties.id, v = values[id];
      const name = res.items.find(d => d.geo === id)?.name || f.properties.name;
      const text = v == null ? "No data"
        : `${fmt.value(v, state.indicator)} ${INDICATORS[state.indicator].unit}<br><span class="muted">Rank ${rank[id]} of ${res.items.length}</span>`;
      l.bindTooltip(`<strong>${name}</strong><br>${text}`, { sticky: true, className: "region-tip" });
      l.on("mouseover", () => l.setStyle({ weight: 2, color: "#17212b" }));
      l.on("mouseout", () => layer.resetStyle(l));
    },
  }).addTo(map);
  drawLegend();
  drawRanking(res.items);
  status(res.items.length ? "" : "No data for this selection");
}

// ----- controls
document.querySelectorAll("#level button").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll("#level button").forEach(b => b.classList.toggle("active", b === btn));
  state.level = Number(btn.dataset.value);
  update();
}));
for (const id of ["indicator", "resid", "year", "month"]) {
  const el = document.getElementById(id);
  el.addEventListener("change", () => { state[id] = id === "year" || id === "month" ? Number(el.value) : el.value; update(); });
}
state.year = Number(document.getElementById("year").value);
update();
