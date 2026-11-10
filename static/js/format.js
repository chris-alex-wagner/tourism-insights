// Shared number formatting helpers
const fmt = {
  int: v => v == null ? "–" : Math.round(v).toLocaleString("en-US"),
  dec: (v, d = 1) => v == null ? "–" : v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }),
  compact: v => v == null ? "–" : Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v),
  value: (v, indicatorKey) => indicatorKey === "avg_length" ? fmt.dec(v, 2) : fmt.int(v),
  short: (v, indicatorKey) => indicatorKey === "avg_length" ? fmt.dec(v, 1) : fmt.compact(v),
};
