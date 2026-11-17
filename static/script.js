/* =========================================================
   RetailScope - vanilla JavaScript (no libraries)
   Only handles the interface: navigation, filters, search,
   tables and the chart lightbox. All charts are Matplotlib PNGs
   and all numbers come from data.js (written by Python).
   ========================================================= */
(function () {
  "use strict";

  const D = window.PROJECT_DATA;
  const IMG = "../visualizations/";
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  if (!D) {
    document.querySelector(".content").innerHTML =
      '<div class="card"><h2 class="card-title">Data not found</h2><p>static/data.js is missing. Run <code>python main.py</code> first.</p></div>';
    return;
  }

  // ---------- formatting helpers ----------
  const nf = new Intl.NumberFormat("en-GB");
  const num = (v, d = 0) => Number(v).toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });
  const gbp = (v, d = 0) => (v < 0 ? "-£" : "£") + num(Math.abs(v), d);
  const short = (v) => {
    const a = Math.abs(v);
    if (a >= 1e6) return (v / 1e6).toFixed(2) + "M";
    if (a >= 1e3) return (v / 1e3).toFixed(1) + "K";
    return num(v);
  };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const monthName = (ym) => {
    const [y, m] = ym.split("-");
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+m - 1] + " " + y;
  };

  function kpiCard(label, value, sub, accent, icon) {
    return `<div class="kpi" style="--accent:${accent}">
      <div class="label"><i>${icon}</i>${label}</div>
      <div class="value">${value}</div>${sub ? `<div class="sub">${sub}</div>` : ""}</div>`;
  }

  function chartCard(c, tag) {
    return `<figure class="chart-card" data-group="${c.group || ""}">
      <h3>${esc(c.title)}${tag ? `<span class="tag">${tag}</span>` : ""}</h3>
      <img src="${IMG + c.file}" alt="${esc(c.title)} chart" loading="lazy" data-caption="${esc(c.caption)}">
      <figcaption>${esc(c.caption)}</figcaption>
      <span class="file">visualizations/${esc(c.file)}</span>
    </figure>`;
  }

  function table(el, headers, rows) {
    el.innerHTML =
      "<thead><tr>" + headers.map((h) => `<th class="${h.n ? "n" : ""}">${h.t}</th>`).join("") + "</tr></thead>" +
      "<tbody>" + rows.map((r) => "<tr>" + r.map((c, i) => `<td class="${headers[i].n ? "n" : ""}">${c}</td>`).join("") + "</tr>").join("") + "</tbody>";
  }

  // =========================================================
  // NAVIGATION (hash based, so links can be shared/bookmarked)
  // =========================================================
  const pages = ["home", "cleaning", "eda", "dashboard", "insights", "about"];
  function showPage() {
    let id = location.hash.replace("#", "") || "home";
    if (!pages.includes(id)) id = "home";
    $$(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + id));
    $$(".nav a").forEach((a) => a.classList.toggle("active", a.dataset.page === id));
    closeMenu();
    window.scrollTo({ top: 0 });
    document.title = $(`.nav a[data-page="${id}"]`).textContent.trim() + " | RetailScope";
  }
  window.addEventListener("hashchange", showPage);

  const sidebar = $("#sidebar"), overlay = $("#overlay"), menuBtn = $("#menuBtn");
  function closeMenu() { sidebar.classList.remove("open"); overlay.classList.remove("show"); menuBtn.setAttribute("aria-expanded", "false"); }
  menuBtn.addEventListener("click", () => {
    const open = !sidebar.classList.contains("open");
    sidebar.classList.toggle("open", open);
    overlay.classList.toggle("show", open);
    menuBtn.setAttribute("aria-expanded", String(open));
  });
  overlay.addEventListener("click", closeMenu);

  // =========================================================
  // PAGE 1: HOME
  // =========================================================
  const C = D.cleaning, ALL = D.periods.all.kpis;
  $("#homeStats").innerHTML =
    kpiCard("Original rows", nf.format(D.dataset.raw_rows), "2 Excel sheets", "var(--blue)", "▤") +
    kpiCard("Cleaned rows", nf.format(D.dataset.clean_rows), D.dataset.clean_columns + " columns after cleaning", "var(--teal)", "✓") +
    kpiCard("Net revenue", "£" + short(ALL.net_revenue), "Product sales minus cancellations", "var(--purple)", "£") +
    kpiCard("Customers", nf.format(ALL.customers), "with a recorded Customer ID", "var(--green)", "☺") +
    kpiCard("Countries", ALL.countries, nf.format(ALL.products) + " products sold", "var(--blue)", "◍");

  $("#datasetInfo").innerHTML = [
    ["Name", "Online Retail II"],
    ["Source", `<a href="${D.dataset.url}" target="_blank" rel="noopener">UCI Machine Learning Repository</a>`],
    ["Period", D.dataset.date_range],
    ["Business", "UK online giftware retailer (many wholesale customers)"],
    ["Original size", `${nf.format(D.dataset.raw_rows)} rows × ${D.dataset.raw_columns} columns`],
    ["Numerical columns", "Quantity, Price (and Customer ID read as a number)"],
    ["Categorical columns", "Invoice, StockCode, Description, Country"],
    ["Date column", "InvoiceDate"],
  ].map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join("");

  // =========================================================
  // PAGE 2: DATA CLEANING
  // =========================================================
  const removed = C.raw_profile.rows - C.clean_profile.rows;
  $("#cleanStats").innerHTML =
    kpiCard("Rows before", nf.format(C.raw_profile.rows), "both sheets combined", "var(--blue)", "▤") +
    kpiCard("Rows after", nf.format(C.clean_profile.rows), "-" + nf.format(removed) + " rows (" + (removed / C.raw_profile.rows * 100).toFixed(1) + "%)", "var(--teal)", "✓") +
    kpiCard("Cancellation rows", nf.format(C.cancellation_rows), nf.format(C.cancellation_invoices) + " invoices, kept", "var(--red)", "↺") +
    kpiCard("Missing Customer ID", nf.format(C.missing_customer_rows), "kept and flagged", "var(--purple)", "?") +
    kpiCard("Columns", C.raw_profile.columns + " → " + C.clean_profile.columns, "derived and flag columns", "var(--green)", "+");

  table($("#sheetTable"), [{ t: "Sheet" }, { t: "Rows", n: 1 }, { t: "From" }, { t: "To" }],
    Object.entries(C.sheets).map(([k, v]) => [k, nf.format(v.rows), v.start.slice(0, 10), v.end.slice(0, 10)]));

  const dtypeMap = { "Customer ID": "CustomerID" };
  table($("#dtypeTable"), [{ t: "Column" }, { t: "Raw type" }, { t: "Clean type" }],
    Object.entries(C.raw_dtypes).map(([k, v]) => {
      const after = C.clean_dtypes[dtypeMap[k] || k] || "-";
      const changed = after !== v;
      return [`<code>${k}</code>`, v, changed ? `<span class="good">${after}</span>` : after];
    }));

  table($("#missingTable"), [{ t: "Column" }, { t: "Missing", n: 1 }, { t: "Percent", n: 1 }, { t: "Treatment" }],
    Object.entries(C.missing_raw).map(([k, v]) => [
      `<code>${k}</code>`,
      v.missing ? `<span class="bad">${nf.format(v.missing)}</span>` : "0",
      v.percent.toFixed(2) + "%",
      k === "Customer ID" ? "Kept; flagged with HasCustomerID" : k === "Description" ? "Filled from same StockCode" : "-",
    ]));
  $("#missingNote").textContent =
    `${nf.format(C.descriptions_filled)} missing descriptions were filled using the name of the same StockCode found elsewhere in the data; ` +
    `${nf.format(C.descriptions_unknown)} had no match and were labelled "UNKNOWN". Customer IDs were not invented.`;

  $("#dupText").innerHTML =
    `Two kinds of duplication were found. First, the two Excel sheets <strong>overlap</strong>: both contain the transactions of
     1-9 December 2010. The script checked that these ${nf.format(C.overlap_rows_removed)} rows are identical before removing one copy.
     Second, ${nf.format(C.duplicates_removed)} rows were <strong>exact duplicates</strong> (identical in all eight columns) and were
     removed with <code>drop_duplicates()</code>.`;
  $("#dupStats").innerHTML =
    `<div><b>${nf.format(C.raw_profile.duplicate_rows)}</b><small>duplicate rows in raw data</small></div>
     <div><b>${nf.format(C.overlap_rows_removed)}</b><small>sheet-overlap rows removed</small></div>
     <div><b>${nf.format(C.duplicates_removed)}</b><small>exact duplicates removed</small></div>`;

  $("#stepList").innerHTML = C.steps.map((s) => {
    const d = s.rows_after - s.rows_before;
    return `<li><span class="num">${s.step}</span><div><strong>${esc(s.action)}</strong><p>${esc(s.reason)}</p></div>
      <span class="delta ${d < 0 ? "minus" : ""}">${d < 0 ? nf.format(d) + " rows" : "no rows removed"}</span></li>`;
  }).join("");

  // cleaning charts placed into their figure slots
  $$("[data-chart^='cleaning-']").forEach((fig) => {
    const c = D.charts.cleaning[+fig.dataset.chart.split("-")[1]];
    fig.outerHTML = chartCard(c);
  });

  const fmtCell = (v) => (typeof v === "number" ? (Number.isInteger(v) ? nf.format(v) : num(v, 2)) : esc(v));
  table($("#beforeAfter"), [{ t: "Metric" }, { t: "Before", n: 1 }, { t: "After", n: 1 }, { t: "Note" }],
    D.before_after.map((r) => [r.Metric, fmtCell(r.Before), fmtCell(r.After), `<span class="muted">${esc(r.Note)}</span>`]));

  function renderDict(q = "") {
    q = q.toLowerCase();
    const rows = D.data_dictionary.filter((r) => (r.Column + r.Description + r.Source).toLowerCase().includes(q));
    table($("#dictTable"), [{ t: "Column" }, { t: "Type" }, { t: "Source" }, { t: "Description" }, { t: "Example" }],
      rows.map((r) => [`<code>${r.Column}</code>`, r.Type, r.Source, esc(r.Description), `<span class="muted">${esc(r.Example)}</span>`]));
  }
  renderDict();
  $("#dictSearch").addEventListener("input", (e) => renderDict(e.target.value));

  // =========================================================
  // PAGE 3: EDA
  // =========================================================
  table($("#statsTable"),
    [{ t: "Variable" }, { t: "Count", n: 1 }, { t: "Mean", n: 1 }, { t: "Median", n: 1 }, { t: "Std", n: 1 }, { t: "Min", n: 1 }, { t: "Q1", n: 1 }, { t: "Q3", n: 1 }, { t: "Max", n: 1 }, { t: "Skew", n: 1 }],
    D.stats.map((s) => [s.Variable, nf.format(s.Count), num(s.Mean, 2), num(s.Median, 2), num(s.Std, 2), num(s.Min, 2), num(s.Q1, 2), num(s.Q3, 2), num(s.Max, 2), num(s.Skewness, 2)]));

  const groupNames = { trend: "Trend", product: "Product", customer: "Customer", country: "Country", distribution: "Distribution", correlation: "Correlation", cancellation: "Cancellation" };
  $("#edaCharts").innerHTML = D.charts.eda.map((c) => chartCard(c, groupNames[c.group])).join("");
  // wide layout for time-series charts
  $$("#edaCharts .chart-card").forEach((f, i) => {
    if (["eda_01", "eda_12", "eda_13"].some((k) => D.charts.eda[i].file.includes(k))) f.classList.add("wide");
  });

  function setupChips(barId, gridId) {
    $(barId).addEventListener("click", (e) => {
      const b = e.target.closest(".chip");
      if (!b) return;
      $$(barId + " .chip").forEach((c) => c.classList.toggle("active", c === b));
      const g = b.dataset.group;
      $$(gridId + " .chart-card").forEach((card) => card.classList.toggle("hide", g !== "all" && card.dataset.group !== g));
    });
  }
  setupChips("#edaFilters", "#edaCharts");

  function renderCorr(method) {
    const cols = D.correlation.columns, m = D.correlation[method];
    const cell = (v) => {
      const a = Math.abs(v), col = v >= 0 ? "248,113,113" : "59,130,246";
      return `<span style="display:block;padding:2px 6px;border-radius:6px;background:rgba(${col},${(a * 0.55).toFixed(2)})">${v.toFixed(2)}</span>`;
    };
    table($("#corrTable"), [{ t: "" }].concat(cols.map((c) => ({ t: c, n: 1 }))),
      m.map((row, i) => [`<strong>${cols[i]}</strong>`].concat(row.map(cell))));
  }
  renderCorr("spearman");
  $("#corrToggle").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    $$("#corrToggle button").forEach((x) => x.classList.toggle("active", x === b));
    renderCorr(b.dataset.method);
  });

  // =========================================================
  // PAGE 4: DASHBOARD
  // =========================================================
  let period = "all", productLimit = 15, productQuery = "", productSort = "revenue";
  const selected = new Set();

  function renderDashboard() {
    const P = D.periods[period], k = P.kpis;
    $("#periodLabel").textContent = P.label + " · all values in GBP (£), net of cancellations unless stated";
    $("#dashKpis").innerHTML =
      kpiCard("Total revenue (net)", gbp(k.net_revenue), "Gross sales " + gbp(k.gross_sales), "var(--blue)", "£") +
      kpiCard("Total orders", nf.format(k.orders), k.items_per_order + " lines per order", "var(--purple)", "▣") +
      kpiCard("Total customers", nf.format(k.customers), k.repeat_customer_rate.toFixed(1) + "% ordered again", "var(--teal)", "☺") +
      kpiCard("Quantity sold", short(k.units_sold), "units on sale invoices", "var(--green)", "#") +
      kpiCard("Average order value", gbp(k.avg_order_value, 2), "median " + gbp(k.median_order_value, 2), "var(--blue)", "⌀") +
      kpiCard("Cancellation rate", k.cancellation_rate.toFixed(1) + "%", nf.format(k.cancelled_invoices) + " cancelled invoices", "var(--red)", "↺");
    $("#dashKpis2").innerHTML =
      kpiCard("Cancelled value", gbp(k.cancelled_value), k.cancellation_value_rate.toFixed(1) + "% of gross sales", "var(--red)", "−") +
      kpiCard("Products sold", nf.format(k.products), "", "var(--purple)", "◫") +
      kpiCard("Countries", k.countries, "", "var(--teal)", "◍") +
      kpiCard("Net units", short(k.net_units), "after returns", "var(--green)", "Σ");

    const activeGroup = ($("#dashFilters .chip.active") || {}).dataset?.group || "all";
    $("#dashCharts").innerHTML = D.charts.dashboard[period].map((c) => chartCard(c)).join("");
    $$("#dashCharts .chart-card").forEach((card) => card.classList.toggle("hide", activeGroup !== "all" && card.dataset.group !== activeGroup));

    renderProducts();
    renderCountries();
    table($("#monthTable"), [{ t: "Month" }, { t: "Net revenue", n: 1 }, { t: "Orders", n: 1 }, { t: "Customers", n: 1 }],
      P.monthly.map((m) => [monthName(m.month), gbp(m.revenue), nf.format(m.orders), nf.format(m.customers)]));
  }

  function renderProducts() {
    const list = D.periods[period].products;
    const q = productQuery.toLowerCase();
    let rows = list.filter((p) => !q || p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q));
    const key = productSort.replace("-asc", "");
    rows = rows.slice().sort((a, b) => (productSort.endsWith("-asc") ? a[key] - b[key] : b[key] - a[key]));
    const shown = rows.slice(0, productLimit);
    const rankOf = new Map(list.map((p, i) => [p.code + p.name, i + 1]));
    table($("#productTable"),
      [{ t: "" }, { t: "Rank", n: 1 }, { t: "Product" }, { t: "Code" }, { t: "Net revenue", n: 1 }, { t: "Units", n: 1 }, { t: "Orders", n: 1 }, { t: "Customers", n: 1 }, { t: "Median price", n: 1 }, { t: "Cancelled", n: 1 }],
      shown.map((p) => {
        const id = p.code + "|" + p.name;
        return [`<input type="checkbox" data-id="${esc(id)}" ${selected.has(id) ? "checked" : ""} aria-label="Compare ${esc(p.name)}">`,
          "#" + rankOf.get(p.code + p.name), esc(p.name), `<code>${esc(p.code)}</code>`, gbp(p.revenue), nf.format(p.units),
          nf.format(p.orders), nf.format(p.customers), gbp(p.price, 2), p.cancelled ? `<span class="bad">${nf.format(p.cancelled)}</span>` : "0"];
      }));
    if (!shown.length) $("#productTable tbody").innerHTML = '<tr><td colspan="10" class="muted">No products match your search.</td></tr>';
    $("#productCount").textContent = `Showing ${shown.length} of ${nf.format(rows.length)} products`;
    $("#productMore").hidden = shown.length >= rows.length;
    renderCompare();
  }

  function renderCompare() {
    const box = $("#compareBox");
    const list = D.periods[period].products;
    const items = [...selected].map((id) => list.find((p) => p.code + "|" + p.name === id)).filter(Boolean);
    if (!items.length) { box.hidden = true; return; }
    box.hidden = false;
    const fields = [["revenue", "Net revenue", (v) => gbp(v)], ["units", "Units", (v) => nf.format(v)], ["orders", "Orders", (v) => nf.format(v)],
      ["customers", "Customers", (v) => nf.format(v)], ["price", "Median price", (v) => gbp(v, 2)], ["cancelled", "Cancelled units", (v) => nf.format(v)]];
    box.innerHTML = items.map((p) => {
      const other = items.find((x) => x !== p);
      return `<div class="side"><h4>${esc(p.name)} <code>${esc(p.code)}</code></h4><dl>` +
        fields.map(([f, label, fmt]) => {
          const better = other && (f === "cancelled" ? p[f] < other[f] : p[f] > other[f]);
          return `<dt>${label}</dt><dd class="${better ? "win" : ""}">${fmt(p[f])}</dd>`;
        }).join("") + "</dl></div>";
    }).join("") + (items.length === 1 ? '<div class="side muted">Tick one more product to compare.</div>' : "");
  }

  $("#productTable").addEventListener("change", (e) => {
    if (e.target.type !== "checkbox") return;
    const id = e.target.dataset.id;
    if (e.target.checked) {
      if (selected.size >= 2) selected.delete([...selected][0]);
      selected.add(id);
    } else selected.delete(id);
    renderProducts();
  });
  $("#productSearch").addEventListener("input", (e) => { productQuery = e.target.value; productLimit = 15; renderProducts(); });
  $("#productSort").addEventListener("change", (e) => { productSort = e.target.value; renderProducts(); });
  $("#productMore").addEventListener("click", () => { productLimit += 25; renderProducts(); });

  function renderCountries() {
    const list = D.periods[period].countries;
    const total = list.reduce((s, c) => s + c.revenue, 0);
    const max = Math.max(...list.map((c) => c.revenue));
    const q = ($("#countrySearch").value || "").toLowerCase();
    table($("#countryTable"), [{ t: "Country" }, { t: "Net revenue", n: 1 }, { t: "Share", n: 1 }, { t: "Orders", n: 1 }, { t: "Customers", n: 1 }, { t: "Avg order", n: 1 }],
      list.filter((c) => c.name.toLowerCase().includes(q)).map((c) => [
        esc(c.name), gbp(c.revenue),
        `<span class="share"><b style="width:${Math.max(2, (c.revenue / max) * 40)}px"></b>${(c.revenue / total * 100).toFixed(1)}%</span>`,
        nf.format(c.orders), nf.format(c.customers), gbp(c.aov)]));
  }
  $("#countrySearch").addEventListener("input", renderCountries);

  $("#periodToggle").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    $$("#periodToggle button").forEach((x) => x.classList.toggle("active", x === b));
    period = b.dataset.period;
    selected.clear();
    renderDashboard();
  });
  setupChips("#dashFilters", "#dashCharts");

  // =========================================================
  // PAGE 5: INSIGHTS
  // =========================================================
  $("#findings").innerHTML = D.findings.map((f, i) =>
    `<article class="finding"><span class="n">FINDING ${String(i + 1).padStart(2, "0")}</span><h3>${esc(f.title)}</h3><p>${esc(f.text)}</p></article>`).join("");

  const X = D.extra, k10 = D.periods["2010"].kpis, k11 = D.periods["2011"].kpis;
  $("#trendList").innerHTML = [
    `Revenue peaks every November; the busiest month overall was ${monthName(X.peak_month)} (${gbp(X.peak_month_revenue)}).`,
    `Comparable Jan-Nov revenue changed by ${X.yoy_jan_nov > 0 ? "+" : ""}${X.yoy_jan_nov.toFixed(1)}% from 2010 to 2011.`,
    `Average order value: ${gbp(k10.avg_order_value, 2)} in 2010 and ${gbp(k11.avg_order_value, 2)} in 2011.`,
    `Cancellation rate: ${k10.cancellation_rate.toFixed(1)}% of invoices in 2010 and ${k11.cancellation_rate.toFixed(1)}% in 2011.`,
    `Customers with a recorded ID: ${nf.format(k10.customers)} in 2010 and ${nf.format(k11.customers)} in 2011.`,
  ].map((t) => `<li>${esc(t)}</li>`).join("");

  const low = X.lowest_products[0];
  $("#discoveryLowest").textContent =
    `Some products lose money overall: among products with at least 20 orders, "${low.name}" has the lowest net revenue (${gbp(low.revenue)}) because returns outweigh sales.`;

  $("#conclusion").textContent =
    `After careful cleaning, ${nf.format(D.dataset.clean_rows)} transactions describe a stable, highly seasonal wholesale business that earned ` +
    `${gbp(ALL.net_revenue)} in net product revenue between ${D.dataset.date_range}. Most revenue comes from the United Kingdom ` +
    `(${X.uk_share.toFixed(1)}%), from a loyal core of customers (top 20% = ${X.top20_share.toFixed(1)}% of revenue) and from the ` +
    `September-November gift season. The project shows that honest cleaning decisions - keeping cancellations as negative revenue, ` +
    `flagging rather than deleting unusual rows, and removing the hidden sheet overlap - change the results noticeably and make ` +
    `the final insights trustworthy.`;
  $("#genTime").textContent = "Results generated by Python on " + D.generated;

  // =========================================================
  // LIGHTBOX (click any chart to enlarge)
  // =========================================================
  const lb = $("#lightbox");
  document.addEventListener("click", (e) => {
    const img = e.target.closest(".chart-card img");
    if (!img) return;
    $("#lbImg").src = img.src;
    $("#lbImg").alt = img.alt;
    $("#lbCap").textContent = img.dataset.caption || "";
    lb.hidden = false;
  });
  const closeLb = () => { lb.hidden = true; };
  $("#lbClose").addEventListener("click", closeLb);
  lb.addEventListener("click", (e) => { if (e.target === lb) closeLb(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeLb(); closeMenu(); } });

  // start
  renderDashboard();
  showPage();
})();
