"""
exploratory_analysis.py
=======================
Foundation of Data Science - Capstone Project
Online Retail II (UCI) : Exploratory Data Analysis and Visualization

Reads the cleaned dataset produced by data_cleaning.py and:
  * computes descriptive statistics, trends, product / customer / country results
  * creates every chart with Matplotlib and saves it as a PNG
        visualizations/cleaning/   charts for the Data Cleaning page
        visualizations/eda/        charts for the EDA page
        visualizations/dashboard/  one set of charts per period (All, 2010, 2011)
  * writes static/data.js - the numbers the website shows (KPIs, tables, captions)
  * writes reports/eda_summary.txt and reports/statistics_summary.csv

Libraries: pandas, matplotlib and the Python standard library (no NumPy import).

Run from the project root:
    python analysis/exploratory_analysis.py
"""

import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib

matplotlib.use("Agg")  # draw to files, no window needed
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent.parent
CLEAN_FILE = ROOT / "dataset" / "cleaned_dataset.csv.gz"
if not CLEAN_FILE.exists():
    CLEAN_FILE = ROOT / "dataset" / "cleaned_dataset.csv"
CLEAN_REPORT = ROOT / "reports" / "cleaning_report.json"
VIS = ROOT / "visualizations"
OUT_JS = ROOT / "static" / "data.js"
REPORTS = ROOT / "reports"
for sub in ["cleaning", "eda", "dashboard"]:
    (VIS / sub).mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Chart theme - matches the website's dark palette
# --------------------------------------------------------------------------
BG = "#172338"        # card background (charts blend into website cards)
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
GRID = "#2A3A55"
BLUE = "#3B82F6"
PURPLE = "#8B5CF6"
TEAL = "#14B8A6"
GREEN = "#22C55E"
RED = "#F87171"
AMBER = "#F59E0B"     # second series colour (clearly different from blue for colour-blind readers)

for weight in ["Regular", "Medium", "SemiBold", "Bold"]:
    font_path = ROOT / "static" / "fonts" / f"Inter-{weight}.otf"
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"],
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "savefig.facecolor": BG,
    "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED,
    "axes.titlecolor": TEXT,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.titlepad": 14,
    "axes.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "legend.frameon": False,
    "legend.labelcolor": TEXT,
    "legend.fontsize": 10,
    "text.color": TEXT,
    "figure.dpi": 100,
    "axes.axisbelow": True,
})

# Colour maps that fit the dark theme (dark navy -> blue, and blue <-> grey <-> red)
from matplotlib.colors import LinearSegmentedColormap
SEQ_CMAP = LinearSegmentedColormap.from_list("navy_blue", ["#1B2A42", "#1E40AF", BLUE, "#93C5FD"])
DIV_CMAP = LinearSegmentedColormap.from_list("blue_red", [BLUE, "#334155", RED])

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def gbp(x, decimals=0):
    """Format a number as pounds, e.g. £1,234."""
    sign = "-" if x < 0 else ""
    return f"{sign}£{abs(x):,.{decimals}f}"


def short_gbp(x, _pos=None):
    """Axis label format: £1.2M, £350K."""
    if abs(x) >= 1e6:
        return f"£{x / 1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"£{x / 1e3:.0f}K"
    return f"£{x:.0f}"


def short_num(x, _pos=None):
    if abs(x) >= 1e6:
        return f"{x / 1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"{x / 1e3:.0f}K"
    return f"{x:.0f}"


def save(fig, folder, name):
    path = VIS / folder / name
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return f"{folder}/{name}"


def trim(text, n=34):
    text = str(text).title()
    return text if len(text) <= n else text[: n - 1] + "…"


def barh(ax, labels, values, color, fmt=short_gbp):
    """Horizontal bar chart with the largest value on top and value labels."""
    labels = list(labels)[::-1]
    values = list(values)[::-1]
    bars = ax.barh(labels, values, color=color, height=0.68)
    ax.xaxis.set_major_formatter(FuncFormatter(fmt))
    ax.grid(axis="y", visible=False)
    vmax = max(values) if values else 1
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + vmax * 0.01, bar.get_y() + bar.get_height() / 2,
                fmt(v), va="center", fontsize=9, color=TEXT)
    ax.set_xlim(0, vmax * 1.15)


# ==========================================================================
# LOAD DATA
# ==========================================================================
print("Loading cleaned dataset ...")
df = pd.read_csv(CLEAN_FILE, parse_dates=["InvoiceDate"],
                 dtype={"Invoice": "string", "StockCode": "string", "CustomerID": "string"})
clean = json.loads(CLEAN_REPORT.read_text(encoding="utf-8"))
print(f"  {len(df):,} rows, {df.shape[1]} columns")

# Analysis base: product lines that are sales or cancellations.
# Cancellations carry negative revenue, so summing Revenue gives NET revenue.
base = df[df["IsProduct"] & df["TransactionType"].isin(["Sale", "Cancellation"])].copy()
SNAPSHOT = df["InvoiceDate"].max().normalize() + pd.Timedelta(days=1)

PERIODS = {
    "all": ("All data (Dec 2009 - Dec 2011)", base),
    "2010": ("Year 2010 (Jan - Dec)", base[base["Year"] == 2010]),
    "2011": ("Year 2011 (Jan - 9 Dec)", base[base["Year"] == 2011]),
}


# ==========================================================================
# HELPER CALCULATIONS
# ==========================================================================
def kpis(data):
    sales = data[data["TransactionType"] == "Sale"]
    canc = data[data["TransactionType"] == "Cancellation"]
    orders = sales["Invoice"].nunique()
    canc_inv = canc["Invoice"].nunique()
    custs = sales["CustomerID"].dropna()
    cust_orders = sales.dropna(subset=["CustomerID"]).groupby("CustomerID")["Invoice"].nunique()
    gross = sales["Revenue"].sum()
    return {
        "net_revenue": round(float(data["Revenue"].sum()), 2),
        "gross_sales": round(float(gross), 2),
        "cancelled_value": round(float(-canc["Revenue"].sum()), 2),
        "orders": int(orders),
        "customers": int(custs.nunique()),
        "countries": int(sales["Country"].nunique()),
        "products": int(sales["StockCode"].nunique()),
        "units_sold": int(sales["Quantity"].sum()),
        "net_units": int(data["Quantity"].sum()),
        "avg_order_value": round(float(gross / orders), 2) if orders else 0,
        "median_order_value": round(float(sales.groupby("Invoice")["Revenue"].sum().median()), 2),
        "cancellation_rate": round(canc_inv / (orders + canc_inv) * 100, 2) if orders else 0,
        "cancellation_value_rate": round(float(-canc["Revenue"].sum() / gross * 100), 2) if gross else 0,
        "cancelled_invoices": int(canc_inv),
        "repeat_customer_rate": round(float((cust_orders > 1).mean() * 100), 2) if len(cust_orders) else 0,
        "items_per_order": round(float(sales.groupby("Invoice")["StockCode"].count().mean()), 1),
    }


def product_table(data):
    sales = data[data["TransactionType"] == "Sale"]
    canc = data[data["TransactionType"] == "Cancellation"]
    t = data.groupby(["StockCode", "Description"]).agg(
        net_revenue=("Revenue", "sum"), net_units=("Quantity", "sum"))
    t["orders"] = sales.groupby(["StockCode", "Description"])["Invoice"].nunique()
    t["customers"] = sales.groupby(["StockCode", "Description"])["CustomerID"].nunique()
    t["avg_price"] = sales.groupby(["StockCode", "Description"])["Price"].median()
    t["cancelled_units"] = -canc.groupby(["StockCode", "Description"])["Quantity"].sum()
    t = t.fillna(0).reset_index().sort_values("net_revenue", ascending=False)
    return t


def customer_table(data):
    known = data.dropna(subset=["CustomerID"])
    sales = known[known["TransactionType"] == "Sale"]
    c = sales.groupby("CustomerID").agg(
        Frequency=("Invoice", "nunique"),
        GrossSales=("Revenue", "sum"),
        Units=("Quantity", "sum"),
        DistinctProducts=("StockCode", "nunique"),
        FirstPurchase=("InvoiceDate", "min"),
        LastPurchase=("InvoiceDate", "max"),
        Country=("Country", "first"),
    )
    c["Monetary"] = known.groupby("CustomerID")["Revenue"].sum()  # net of cancellations
    c["Recency"] = (SNAPSHOT - c["LastPurchase"]).dt.days
    c["Tenure"] = (c["LastPurchase"] - c["FirstPurchase"]).dt.days
    c["AvgOrderValue"] = c["GrossSales"] / c["Frequency"]
    return c


# ==========================================================================
# CLEANING-PAGE CHARTS
# ==========================================================================
print("Creating data-cleaning charts ...")
charts = {"cleaning": [], "eda": [], "dashboard": {}}

# C1 - missing values
miss = pd.Series({k: v["percent"] for k, v in clean["missing_raw"].items()})
miss = miss.sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(9, 4.6))
colors = [RED if v > 0 else GRID for v in miss.values]
bars = ax.barh(miss.index, miss.values, color=colors, height=0.6)
for bar, (col, v) in zip(bars, miss.items()):
    n = clean["missing_raw"][col]["missing"]
    ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2,
            f"{v:.2f}%  ({n:,} rows)", va="center", fontsize=9, color=TEXT if v else MUTED)
ax.set_xlim(0, max(miss.values) * 1.45)
ax.set_xlabel("Share of rows missing (%)")
ax.set_title("Missing values in the original dataset", loc="left")
ax.grid(axis="y", visible=False)
charts["cleaning"].append({
    "file": save(fig, "cleaning", "clean_01_missing_values.png"),
    "title": "Missing values by column",
    "caption": f"Only two columns have gaps. Customer ID is missing in {clean['missing_raw']['Customer ID']['percent']:.1f}% "
               f"of rows and Description in {clean['missing_raw']['Description']['percent']:.2f}%. "
               "All other columns are complete.",
})

# C2 - row count waterfall
steps = [("Original rows", clean["raw_profile"]["rows"]),
         ("Sheet overlap removed", -clean["overlap_rows_removed"]),
         ("Duplicates removed", -clean["duplicates_removed"]),
         ("Cleaned rows", clean["clean_profile"]["rows"])]
fig, ax = plt.subplots(figsize=(9, 4.6))
running = 0
for i, (label, val) in enumerate(steps):
    if i in (0, len(steps) - 1):
        ax.bar(i, val, color=BLUE, width=0.6)
        ax.text(i, val * 1.01, f"{val:,}", ha="center", va="bottom", fontsize=10, color=TEXT)
        running = val
    else:
        ax.bar(i, -val, bottom=running + val, color=RED, width=0.6)
        running += val
        ax.text(i, running - 1500, f"{val:,}", ha="center", va="top", fontsize=10, color=RED)
ax.set_xticks(range(len(steps)))
ax.set_xticklabels([s[0] for s in steps])
ax.set_ylim(clean["clean_profile"]["rows"] * 0.95, clean["raw_profile"]["rows"] * 1.02)
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x / 1e6:.3f}M"))
ax.set_title("How the row count changed during cleaning", loc="left")
ax.grid(axis="x", visible=False)
removed = clean["raw_profile"]["rows"] - clean["clean_profile"]["rows"]
charts["cleaning"].append({
    "file": save(fig, "cleaning", "clean_02_row_changes.png"),
    "title": "Rows removed during cleaning",
    "caption": f"{removed:,} rows ({removed / clean['raw_profile']['rows'] * 100:.1f}%) were removed: "
               f"{clean['overlap_rows_removed']:,} rows that appear in both Excel sheets and "
               f"{clean['duplicates_removed']:,} exact duplicates. Note the y-axis starts near 1.0M to make the small changes visible.",
})

# C3 - transaction types
tt = pd.Series(clean["transaction_types"]).sort_values()
fig, ax = plt.subplots(figsize=(9, 4.6))
tt_colors = {"Sale": BLUE, "Cancellation": RED, "Stock Adjustment": PURPLE,
             "Zero-Price Entry": TEAL, "Bad Debt Adjustment": AMBER}
bars = ax.barh(tt.index, tt.values, color=[tt_colors[k] for k in tt.index], height=0.6)
ax.set_xscale("log")
for bar, v in zip(bars, tt.values):
    ax.text(bar.get_width() * 1.15, bar.get_y() + bar.get_height() / 2, f"{v:,}",
            va="center", fontsize=9.5, color=TEXT)
ax.set_xlim(1, tt.max() * 8)
ax.xaxis.set_major_formatter(FuncFormatter(short_num))
ax.set_xlabel("Number of rows (log scale)")
ax.set_title("Every row classified - nothing blindly deleted", loc="left")
ax.grid(axis="y", visible=False)
charts["cleaning"].append({
    "file": save(fig, "cleaning", "clean_03_transaction_types.png"),
    "title": "Transaction types after cleaning",
    "caption": f"{clean['transaction_types']['Sale']:,} rows are normal sales. "
               f"{clean['transaction_types']['Cancellation']:,} cancellation rows and "
               f"{clean['transaction_types']['Stock Adjustment']:,} stock write-offs are kept and labelled "
               "so they can be analysed separately. A log scale is used because the groups differ greatly in size.",
})


# ==========================================================================
# EDA CHARTS (whole period)
# ==========================================================================
print("Creating EDA charts ...")
sales_all = base[base["TransactionType"] == "Sale"]
canc_all = base[base["TransactionType"] == "Cancellation"]
monthly = base.groupby("YearMonth")["Revenue"].sum()
monthly_orders = sales_all.groupby("YearMonth")["Invoice"].nunique()

# E1 - monthly revenue trend
fig, ax = plt.subplots(figsize=(11, 4.8))
x = list(range(len(monthly)))
ax.plot(x, monthly.values, color=BLUE, linewidth=2.2, marker="o", markersize=5)
ax.fill_between(x, monthly.values, color=BLUE, alpha=0.12)
ax.set_xticks(x)
ax.set_xticklabels([f"{MONTH_ABBR[int(m[5:]) - 1]}\n{m[:4]}" if m.endswith(("-01", "-12")) or i == 0
                    else MONTH_ABBR[int(m[5:]) - 1] for i, m in enumerate(monthly.index)], fontsize=8.5)
ax.yaxis.set_major_formatter(FuncFormatter(short_gbp))
peak_m = monthly.idxmax()
ax.annotate(f"Peak: {peak_m}\n{gbp(monthly.max())}", xy=(list(monthly.index).index(peak_m), monthly.max()),
            xytext=(-120, -10), textcoords="offset points", color=TEXT, fontsize=9,
            arrowprops=dict(arrowstyle="-", color=MUTED))
ax.set_ylabel("Net revenue")
ax.set_title("Monthly net revenue, Dec 2009 - Dec 2011", loc="left")
ax.set_ylim(0, monthly.max() * 1.15)
low_m = monthly.idxmin()
charts["eda"].append({
    "file": save(fig, "eda", "eda_01_monthly_revenue_trend.png"),
    "group": "trend", "title": "Monthly revenue trend",
    "caption": f"Revenue follows a strong yearly cycle: it climbs from September and peaks in November "
               f"({peak_m}: {gbp(monthly.max())}). The lowest month is {low_m} ({gbp(monthly.min())}), "
               "which only covers 1-9 December 2011 because the data ends there.",
})

# E2 - YoY comparison (2010 vs 2011, same months)
m10 = base[base["Year"] == 2010].groupby("Month")["Revenue"].sum()
m11 = base[base["Year"] == 2011].groupby("Month")["Revenue"].sum()
fig, ax = plt.subplots(figsize=(11, 4.8))
w = 0.38
ax.bar([m - w / 2 for m in m10.index], m10.values, width=w, color=BLUE, label="2010")
ax.bar([m - (-w / 2) for m in m11.index], m11.values, width=w, color=AMBER, label="2011")
ax.set_xticks(range(1, 13))
ax.set_xticklabels(MONTH_ABBR)
ax.yaxis.set_major_formatter(FuncFormatter(short_gbp))
ax.set_ylabel("Net revenue")
ax.legend(loc="upper left")
ax.grid(axis="x", visible=False)
ax.set_title("2010 vs 2011 by month", loc="left")
jan_nov_10 = m10.loc[1:11].sum()
jan_nov_11 = m11.loc[1:11].sum()
yoy = (jan_nov_11 - jan_nov_10) / jan_nov_10 * 100
charts["eda"].append({
    "file": save(fig, "eda", "eda_02_yearly_comparison.png"),
    "group": "trend", "title": "Year-on-year comparison",
    "caption": f"Comparing the same months (Jan-Nov), 2011 earned {gbp(jan_nov_11)} against {gbp(jan_nov_10)} "
               f"in 2010, a change of {yoy:+.1f}%. The seasonal shape is almost identical in both years. "
               "December 2011 is short because the data stops on 9 December.",
})

# E3 - top products by revenue
prod_all = product_table(base)
top10 = prod_all.head(10)
fig, ax = plt.subplots(figsize=(10, 5.2))
barh(ax, [trim(d) for d in top10["Description"]], top10["net_revenue"], BLUE)
ax.set_xlabel("Net revenue")
ax.set_title("Top 10 products by net revenue", loc="left")
top10_share = top10["net_revenue"].sum() / prod_all["net_revenue"].sum() * 100
charts["eda"].append({
    "file": save(fig, "eda", "eda_03_top_products_revenue.png"),
    "group": "product", "title": "Top products by revenue",
    "caption": f"'{top10.iloc[0]['Description'].title()}' is the best seller at {gbp(top10.iloc[0]['net_revenue'])}. "
               f"The top 10 products make up {top10_share:.1f}% of net revenue out of "
               f"{kpis(base)['products']:,} products sold, so sales are spread across a very wide catalogue.",
})

# E4 - top products by units
topq = prod_all.sort_values("net_units", ascending=False).head(10)
fig, ax = plt.subplots(figsize=(10, 5.2))
barh(ax, [trim(d) for d in topq["Description"]], topq["net_units"], TEAL, fmt=short_num)
ax.set_xlabel("Net units sold")
ax.set_title("Top 10 products by units sold", loc="left")
overlap = len(set(topq["StockCode"]) & set(top10["StockCode"]))
charts["eda"].append({
    "file": save(fig, "eda", "eda_04_top_products_units.png"),
    "group": "product", "title": "Top products by quantity",
    "caption": f"Volume leaders are mostly cheap items such as cake cases and small ornaments; "
               f"'{topq.iloc[0]['Description'].title()}' sold {topq.iloc[0]['net_units']:,.0f} units. "
               f"Only {overlap} products appear in both the revenue and the units top 10.",
})

# E5 - most cancelled products (lowest performers)
canc_prod = (canc_all.groupby("Description")["Revenue"].sum() * -1)
canc_prod = canc_prod[canc_prod.index != "UNKNOWN"].sort_values(ascending=False)
# exclude the two data-entry errors (74,215 and 80,995 units) so the chart shows normal returns
error_items = df.loc[df["Quantity"].abs() >= 70000, "Description"].unique().tolist()
canc_plot = canc_prod.drop(labels=error_items, errors="ignore").head(10)
fig, ax = plt.subplots(figsize=(10, 5.2))
barh(ax, [trim(d) for d in canc_plot.index], canc_plot.values, RED)
ax.set_xlabel("Value of cancelled lines")
ax.set_title("Products with the highest cancellation value", loc="left")
charts["eda"].append({
    "file": save(fig, "eda", "eda_05_most_cancelled_products.png"),
    "group": "product", "title": "Most cancelled products",
    "caption": f"'{canc_plot.index[0].title()}' has the largest cancelled value ({gbp(canc_plot.iloc[0])}). "
               "Two one-off errors (orders of 74,215 and 80,995 units that were reversed the same day) are left out "
               "of this chart so it shows normal returns.",
})

# E6 - countries (excluding UK) + share pie
country = base.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
uk_share = country["United Kingdom"] / country.sum() * 100
intl = country.drop("United Kingdom").head(10)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1.6, 1]})
barh(ax1, intl.index, intl.values, PURPLE)
ax1.set_title("Top 10 international markets", loc="left")
ax1.set_xlabel("Net revenue")
pie_vals = [country["United Kingdom"], country.drop("United Kingdom").sum()]
wedges, _t, autot = ax2.pie(pie_vals, colors=[BLUE, PURPLE], startangle=90, autopct="%1.1f%%",
                            pctdistance=0.78, wedgeprops=dict(width=0.38, edgecolor=BG, linewidth=2),
                            textprops=dict(color=TEXT, fontsize=10))
ax2.legend(wedges, ["United Kingdom", "Other countries"], loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=2)
ax2.set_title("Revenue share", loc="center")
charts["eda"].append({
    "file": save(fig, "eda", "eda_06_country_analysis.png"),
    "group": "country", "title": "Country performance",
    "caption": f"The United Kingdom brings in {uk_share:.1f}% of net revenue. Among other markets, "
               f"{intl.index[0]} ({gbp(intl.iloc[0])}), {intl.index[1]} and {intl.index[2]} lead. "
               f"Customers came from {kpis(base)['countries']} countries in total.",
})

# E7 - order value distribution (histogram, log bins)
order_val = sales_all.groupby("Invoice")["Revenue"].sum()
order_val_pos = order_val[order_val > 0]
bins = [10 ** (i / 12) for i in range(0, 12 * 5 + 1)]  # £1 to £100,000, log-spaced (no NumPy needed)
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.hist(order_val_pos, bins=bins, color=BLUE, edgecolor=BG, linewidth=0.6)
ax.set_xscale("log")
ax.xaxis.set_major_formatter(FuncFormatter(short_gbp))
ax.axvline(order_val.median(), color=TEAL, linewidth=2, label=f"Median {gbp(order_val.median())}")
ax.axvline(order_val.mean(), color=AMBER, linewidth=2, linestyle="--", label=f"Mean {gbp(order_val.mean())}")
ax.legend(loc="upper right")
ax.set_xlabel("Order value (log scale)")
ax.set_ylabel("Number of orders")
ax.set_title("Distribution of order values", loc="left")
ax.grid(axis="x", visible=False)
charts["eda"].append({
    "file": save(fig, "eda", "eda_07_order_value_distribution.png"),
    "group": "distribution", "title": "Order value distribution",
    "caption": f"Most orders are worth between {gbp(order_val.quantile(0.25))} and {gbp(order_val.quantile(0.75))} "
               f"(middle 50%). The mean ({gbp(order_val.mean())}) is above the median ({gbp(order_val.median())}) "
               f"because a few very large wholesale orders pull it up - the distribution is right-skewed "
               f"(skewness {order_val.skew():.1f}).",
})

# E8 - box plots of quantity and unit price
sale_lines = sales_all[sales_all["Quantity"] > 0]
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
box_style = dict(patch_artist=True, widths=0.5,
                 medianprops=dict(color=TEXT, linewidth=2),
                 whiskerprops=dict(color=MUTED), capprops=dict(color=MUTED),
                 flierprops=dict(marker="o", markersize=2.5, markerfacecolor=RED, markeredgecolor="none", alpha=0.35))
b1 = ax1.boxplot([sale_lines["Quantity"]], **box_style)
b1["boxes"][0].set(facecolor=TEAL, edgecolor=TEAL, alpha=0.8)
ax1.set_yscale("log")
ax1.set_xticks([1])
ax1.set_xticklabels(["Quantity per line"])
ax1.yaxis.set_major_formatter(FuncFormatter(short_num))
ax1.set_title("Quantity per order line", loc="left")
b2 = ax2.boxplot([sale_lines["Price"]], **box_style)
b2["boxes"][0].set(facecolor=PURPLE, edgecolor=PURPLE, alpha=0.8)
ax2.set_yscale("log")
ax2.set_xticks([1])
ax2.set_xticklabels(["Unit price"])
ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"£{v:g}"))
ax2.set_title("Unit price", loc="left")
for a in (ax1, ax2):
    a.grid(axis="x", visible=False)
charts["eda"].append({
    "file": save(fig, "eda", "eda_08_quantity_price_boxplots.png"),
    "group": "distribution", "title": "Quantity and price spread (box plots)",
    "caption": f"Median line quantity is {sale_lines['Quantity'].median():.0f} units and median unit price is "
               f"{gbp(sale_lines['Price'].median(), 2)}. Red dots are IQR outliers: {clean['quantity_outliers']:,} lines "
               f"above {clean['quantity_iqr_upper']:.0f} units and {clean['price_outliers']:,} above "
               f"{gbp(clean['price_iqr_upper'], 2)}. They are bulk orders, so they were kept. Log scale.",
})

# E9 - Pareto curve of customers
cust = customer_table(base)
cust_pos = cust[cust["Monetary"] >= 1].sort_values("Monetary", ascending=False)  # positive net spend
cum_share = cust_pos["Monetary"].cumsum() / cust_pos["Monetary"].sum() * 100
cust_pct = [(i + 1) / len(cust_pos) * 100 for i in range(len(cust_pos))]
top20_n = math.ceil(len(cust_pos) * 0.2)
top20_share = cum_share.iloc[top20_n - 1]
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(cust_pct, cum_share.values, color=BLUE, linewidth=2.4, label="Customers (sorted by spend)")
ax.plot([0, 100], [0, 100], color=MUTED, linestyle="--", linewidth=1, label="Equal spending")
ax.axvline(20, color=AMBER, linewidth=1)
ax.axhline(top20_share, color=AMBER, linewidth=1)
ax.scatter([20], [top20_share], color=AMBER, s=60, zorder=5)
ax.annotate(f"Top 20% of customers\n= {top20_share:.1f}% of revenue", xy=(20, top20_share),
            xytext=(30, top20_share - 25), color=TEXT, fontsize=10,
            arrowprops=dict(arrowstyle="-", color=MUTED))
ax.set_xlabel("Share of customers (%)")
ax.set_ylabel("Cumulative share of revenue (%)")
ax.set_xlim(0, 100)
ax.set_ylim(0, 102)
ax.legend(loc="lower right")
ax.set_title("Pareto analysis: how concentrated is revenue?", loc="left")
charts["eda"].append({
    "file": save(fig, "eda", "eda_09_customer_pareto.png"),
    "group": "customer", "title": "Customer revenue concentration (Pareto)",
    "caption": f"The top 20% of customers ({top20_n:,} of {len(cust_pos):,} with positive net spend) generate "
               f"{top20_share:.1f}% of identified-customer revenue - close to the classic 80/20 rule. "
               "Keeping these customers is critical.",
})

# E10 - frequency vs monetary scatter
fig, ax = plt.subplots(figsize=(10, 5))
sc = ax.scatter(cust_pos["Frequency"], cust_pos["Monetary"], c=cust_pos["Recency"], cmap="viridis_r",
                s=12, alpha=0.7, edgecolors="none")
ax.set_xscale("log")
ax.set_yscale("log")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: short_gbp(v) if v >= 1 else f"£{v:g}"))
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}"))
cb = fig.colorbar(sc, ax=ax, pad=0.01)
cb.set_label("Days since last purchase", color=MUTED)
cb.ax.yaxis.set_tick_params(color=MUTED, labelcolor=MUTED)
cb.outline.set_visible(False)
ax.set_xlabel("Number of orders (log scale)")
ax.set_ylabel("Net spend (log scale)")
ax.set_title("Customers: order frequency vs spending", loc="left")
r_fm = cust_pos["Frequency"].corr(cust_pos["Monetary"], method="spearman")
charts["eda"].append({
    "file": save(fig, "eda", "eda_10_frequency_vs_spend.png"),
    "group": "customer", "title": "Frequency vs spending (scatter)",
    "caption": f"Customers who order more often spend more (Spearman correlation {r_fm:.2f}). Yellow dots (recent buyers) "
               "sit mostly on the upper right; dark dots on the lower left are one-time buyers who have not "
               "returned for a long time.",
})

# E11 - correlation heatmap (customer level)
corr_cols = ["Recency", "Frequency", "Monetary", "Units", "AvgOrderValue", "DistinctProducts", "Tenure"]
corr = cust_pos[corr_cols].corr(method="spearman").round(2)
fig, ax = plt.subplots(figsize=(8.6, 6.6))
im = ax.imshow(corr.to_numpy(), cmap=DIV_CMAP, vmin=-1, vmax=1)
ax.set_xticks(range(len(corr_cols)))
ax.set_yticks(range(len(corr_cols)))
ax.set_xticklabels(corr_cols, rotation=35, ha="right")
ax.set_yticklabels(corr_cols)
ax.grid(False)
for i in range(len(corr_cols)):
    for j in range(len(corr_cols)):
        v = corr.iloc[i, j]
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9.5,
                color=TEXT)
cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
cb.ax.yaxis.set_tick_params(color=MUTED, labelcolor=MUTED)
cb.outline.set_visible(False)
ax.set_title("Correlation between customer metrics (Spearman)", loc="left")
corr_pairs = []
for i, a in enumerate(corr_cols):
    for b in corr_cols[i + 1:]:
        corr_pairs.append((a, b, corr.loc[a, b]))
corr_pairs.sort(key=lambda t: abs(t[2]), reverse=True)
strong = corr_pairs[0]
neg = min(corr_pairs, key=lambda t: t[2])
charts["eda"].append({
    "file": save(fig, "eda", "eda_11_correlation_heatmap.png"),
    "group": "correlation", "title": "Correlation heatmap",
    "caption": f"Strongest relationship: {strong[0]} and {strong[1]} ({strong[2]:.2f}). Recency is negatively "
               f"related to the others (e.g. {neg[0]} vs {neg[1]}: {neg[2]:.2f}): customers who bought recently "
               "also tend to buy more often and spend more. Spearman is used because the data is highly skewed.",
})

# E12 - weekday x hour heatmap
wh = sales_all.pivot_table(index="DayOfWeek", columns="Hour", values="Revenue", aggfunc="sum", fill_value=0)
wh = wh.reindex([d for d in DAYS if d in wh.index])
fig, ax = plt.subplots(figsize=(11, 4.4))
im = ax.imshow(wh.to_numpy(), cmap=SEQ_CMAP, aspect="auto")
ax.set_xticks(range(len(wh.columns)))
ax.set_xticklabels([f"{h:02d}:00" for h in wh.columns], rotation=45, ha="right", fontsize=8.5)
ax.set_yticks(range(len(wh.index)))
ax.set_yticklabels(wh.index)
ax.grid(False)
cb = fig.colorbar(im, ax=ax, pad=0.01)
cb.ax.yaxis.set_major_formatter(FuncFormatter(short_gbp))
cb.ax.yaxis.set_tick_params(color=MUTED, labelcolor=MUTED)
cb.outline.set_visible(False)
ax.set_title("When do sales happen? Revenue by weekday and hour", loc="left")
day_rev = sales_all.groupby("DayOfWeek")["Revenue"].sum()
hour_rev = sales_all.groupby("Hour")["Revenue"].sum()
sat_rows = int((sales_all["DayOfWeek"] == "Saturday").sum())
charts["eda"].append({
    "file": save(fig, "eda", "eda_12_weekday_hour_heatmap.png"),
    "group": "trend", "title": "Weekday and hour heatmap",
    "caption": f"{day_rev.idxmax()} is the strongest day and {hour_rev.idxmax()}:00 the busiest hour. "
               f"Trading happens between {hour_rev.index.min():02d}:00 and {hour_rev.index.max():02d}:00, "
               f"and Saturday has almost no sales ({sat_rows:,} sale lines in two years), "
               "so the shop clearly trades on business days.",
})

# E13 - cancellation rate by month
inv_m = sales_all.groupby("YearMonth")["Invoice"].nunique()
cinv_m = canc_all.groupby("YearMonth")["Invoice"].nunique().reindex(inv_m.index, fill_value=0)
crate = cinv_m / (inv_m + cinv_m) * 100
fig, ax = plt.subplots(figsize=(11, 4.6))
ax.bar(range(len(crate)), crate.values, color=RED, width=0.7)
avg_rate = kpis(base)["cancellation_rate"]
ax.axhline(avg_rate, color=TEXT, linestyle="--", linewidth=1, label=f"Overall rate {avg_rate:.1f}%")
ax.set_xticks(range(len(crate)))
ax.set_xticklabels([f"{MONTH_ABBR[int(m[5:]) - 1]}\n{m[:4]}" if m.endswith(("-01", "-12")) or i == 0
                    else MONTH_ABBR[int(m[5:]) - 1] for i, m in enumerate(crate.index)], fontsize=8.5)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:.0f}%"))
ax.set_ylabel("Cancelled invoices (% of all invoices)")
ax.legend(loc="upper left")
ax.grid(axis="x", visible=False)
ax.set_title("Cancellation rate by month", loc="left")
charts["eda"].append({
    "file": save(fig, "eda", "eda_13_cancellation_rate.png"),
    "group": "cancellation", "title": "Cancellation patterns",
    "caption": f"{avg_rate:.1f}% of invoices are cancellations, worth {gbp(kpis(base)['cancelled_value'])} "
               f"({kpis(base)['cancellation_value_rate']:.1f}% of gross sales). The highest monthly rate was "
               f"{crate.max():.1f}% in {crate.idxmax()} and the lowest {crate.min():.1f}% in {crate.idxmin()}.",
})


# ==========================================================================
# DASHBOARD CHARTS - one set per period
# ==========================================================================
def spend_bands(c):
    edges = [-1e12, 0, 250, 500, 1000, 2500, 5000, 1e12]
    labels = ["≤ £0", "£1-250", "£250-500", "£500-1K", "£1K-2.5K", "£2.5K-5K", "> £5K"]
    return pd.cut(c["Monetary"], bins=edges, labels=labels).value_counts().reindex(labels)


def dashboard_charts(key, label, data):
    out = []
    sales = data[data["TransactionType"] == "Sale"]
    canc = data[data["TransactionType"] == "Cancellation"]
    tag = f"({label.split(' (')[0]})"

    # D1 monthly revenue
    m = data.groupby("YearMonth")["Revenue"].sum()
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.bar(range(len(m)), m.values, color=BLUE, width=0.72)
    step = 1 if len(m) <= 13 else 2
    ax.set_xticks(range(0, len(m), step))
    ax.set_xticklabels([f"{MONTH_ABBR[int(v[5:]) - 1]} {v[2:4]}" for v in m.index[::step]], rotation=0, fontsize=8.5)
    ax.yaxis.set_major_formatter(FuncFormatter(short_gbp))
    ax.grid(axis="x", visible=False)
    ax.set_title(f"Monthly net revenue {tag}", loc="left")
    out.append({"file": save(fig, "dashboard", f"{key}_01_monthly_revenue.png"), "group": "trend",
                "title": "Monthly revenue",
                "caption": f"Best month: {m.idxmax()} ({gbp(m.max())}). Average month: {gbp(m.mean())}."})

    # D2 top products
    p = product_table(data).head(10)
    fig, ax = plt.subplots(figsize=(10, 5))
    barh(ax, [trim(d, 30) for d in p["Description"]], p["net_revenue"], BLUE)
    ax.set_title(f"Top 10 products {tag}", loc="left")
    out.append({"file": save(fig, "dashboard", f"{key}_02_top_products.png"), "group": "product",
                "title": "Top products",
                "caption": f"#1 is {p.iloc[0]['Description'].title()} with {gbp(p.iloc[0]['net_revenue'])}."})

    # D3 countries excluding UK
    cty = data.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
    ci = cty.drop("United Kingdom", errors="ignore").head(10)
    fig, ax = plt.subplots(figsize=(10, 5))
    barh(ax, ci.index, ci.values, PURPLE)
    ax.set_title(f"Top 10 countries outside the UK {tag}", loc="left")
    out.append({"file": save(fig, "dashboard", f"{key}_03_top_countries.png"), "group": "country",
                "title": "International markets",
                "caption": f"UK share {cty.get('United Kingdom', 0) / cty.sum() * 100:.1f}%; "
                           f"largest export market {ci.index[0]} ({gbp(ci.iloc[0])})."})

    # D4 weekday
    d = sales.groupby("DayOfWeek")["Revenue"].sum().reindex(DAYS, fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar([x[:3] for x in d.index], d.values, color=[TEAL if v == d.max() else "#2F6F78" for v in d.values], width=0.65)
    ax.yaxis.set_major_formatter(FuncFormatter(short_gbp))
    ax.grid(axis="x", visible=False)
    ax.set_title(f"Gross sales by weekday {tag}", loc="left")
    out.append({"file": save(fig, "dashboard", f"{key}_04_weekday.png"), "group": "trend",
                "title": "Sales by weekday",
                "caption": f"{d.idxmax()} is the busiest day ({gbp(d.max())}); Saturday ≈ {gbp(d['Saturday'])}."})

    # D5 hour
    h = sales.groupby("Hour")["Revenue"].sum()
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar([f"{x:02d}" for x in h.index], h.values, color=[TEAL if v == h.max() else "#2F6F78" for v in h.values], width=0.7)
    ax.yaxis.set_major_formatter(FuncFormatter(short_gbp))
    ax.set_xlabel("Hour of day")
    ax.grid(axis="x", visible=False)
    ax.set_title(f"Gross sales by hour {tag}", loc="left")
    out.append({"file": save(fig, "dashboard", f"{key}_05_hourly.png"), "group": "trend",
                "title": "Sales by hour",
                "caption": f"Peak hour {h.idxmax()}:00 ({gbp(h.max())}); "
                           f"{h.loc[10:15].sum() / h.sum() * 100:.0f}% of sales fall between 10:00 and 15:59."})

    # D6 customer spend bands
    c = customer_table(data)
    sb = spend_bands(c)
    fig, ax = plt.subplots(figsize=(9, 4.4))
    bars = ax.bar(sb.index.astype(str), sb.values, color=PURPLE, width=0.65)
    for bar, v in zip(bars, sb.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{v:,}", ha="center", va="bottom", fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Customers")
    ax.set_title(f"Customers by net spend {tag}", loc="left")
    out.append({"file": save(fig, "dashboard", f"{key}_06_customer_spend.png"), "group": "customer",
                "title": "Customer spending bands",
                "caption": f"{len(c):,} identified customers; median net spend {gbp(c['Monetary'].median())}."})

    # D7 order value histogram
    ov = sales.groupby("Invoice")["Revenue"].sum()
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.hist(ov[ov > 0], bins=bins, color=BLUE, edgecolor=BG, linewidth=0.5)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(short_gbp))
    ax.axvline(ov.median(), color=TEAL, linewidth=2, label=f"Median {gbp(ov.median())}")
    ax.legend(loc="upper right")
    ax.set_xlabel("Order value (log scale)")
    ax.set_ylabel("Orders")
    ax.grid(axis="x", visible=False)
    ax.set_title(f"Order value distribution {tag}", loc="left")
    out.append({"file": save(fig, "dashboard", f"{key}_07_order_values.png"), "group": "distribution",
                "title": "Order value distribution",
                "caption": f"{len(ov):,} orders; median {gbp(ov.median())}, mean {gbp(ov.mean())}."})

    # D8 cancellation rate by month
    im_ = sales.groupby("YearMonth")["Invoice"].nunique()
    cm_ = canc.groupby("YearMonth")["Invoice"].nunique().reindex(im_.index, fill_value=0)
    cr = cm_ / (im_ + cm_) * 100
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.bar(range(len(cr)), cr.values, color=RED, width=0.7)
    ax.set_xticks(range(0, len(cr), step))
    ax.set_xticklabels([f"{MONTH_ABBR[int(v[5:]) - 1]} {v[2:4]}" for v in cr.index[::step]], fontsize=8.5)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:.0f}%"))
    ax.grid(axis="x", visible=False)
    ax.set_title(f"Cancellation rate by month {tag}", loc="left")
    out.append({"file": save(fig, "dashboard", f"{key}_08_cancellations.png"), "group": "cancellation",
                "title": "Cancellation rate",
                "caption": f"Highest in {cr.idxmax()} ({cr.max():.1f}%), lowest in {cr.idxmin()} ({cr.min():.1f}%)."})
    return out


print("Creating dashboard charts for each period ...")
dash = {}
for key, (label, data) in PERIODS.items():
    charts["dashboard"][key] = dashboard_charts(key, label, data)
    prod = product_table(data)
    cty = data.groupby("Country").agg(net_revenue=("Revenue", "sum"))
    s = data[data["TransactionType"] == "Sale"]
    cty["orders"] = s.groupby("Country")["Invoice"].nunique()
    cty["customers"] = s.groupby("Country")["CustomerID"].nunique()
    cty["units"] = s.groupby("Country")["Quantity"].sum()
    cty = cty.fillna(0).sort_values("net_revenue", ascending=False).reset_index()
    cty["aov"] = (s.groupby("Country")["Revenue"].sum() / s.groupby("Country")["Invoice"].nunique()).reindex(cty["Country"]).fillna(0).values
    mon = data.groupby("YearMonth").agg(net_revenue=("Revenue", "sum"))
    mon["orders"] = s.groupby("YearMonth")["Invoice"].nunique()
    mon["customers"] = s.groupby("YearMonth")["CustomerID"].nunique()
    mon = mon.fillna(0).reset_index()
    dash[key] = {
        "label": label,
        "kpis": kpis(data),
        "products": [
            {"code": r.StockCode, "name": r.Description.title(), "revenue": round(r.net_revenue, 2),
             "units": int(r.net_units), "orders": int(r.orders), "customers": int(r.customers),
             "price": round(r.avg_price, 2), "cancelled": int(r.cancelled_units)}
            for r in prod[prod["orders"] > 0].itertuples()
        ],
        "countries": [
            {"name": r.Country, "revenue": round(r.net_revenue, 2), "orders": int(r.orders),
             "customers": int(r.customers), "units": int(r.units), "aov": round(r.aov, 2)}
            for r in cty.itertuples()
        ],
        "monthly": [
            {"month": r.YearMonth, "revenue": round(r.net_revenue, 2), "orders": int(r.orders),
             "customers": int(r.customers)} for r in mon.itertuples()
        ],
    }


# ==========================================================================
# STATISTICAL SUMMARY
# ==========================================================================
print("Computing statistics ...")
stat_series = {
    "Quantity per line": sale_lines["Quantity"],
    "Unit price (£)": sale_lines["Price"],
    "Line revenue (£)": sale_lines["Revenue"],
    "Order value (£)": order_val,
    "Items per order": sales_all.groupby("Invoice")["StockCode"].count(),
    "Orders per customer": cust["Frequency"],
    "Net spend per customer (£)": cust["Monetary"],
}
stats_rows = []
for name, s in stat_series.items():
    stats_rows.append({
        "Variable": name, "Count": int(s.count()), "Mean": round(float(s.mean()), 2),
        "Median": round(float(s.median()), 2), "Std": round(float(s.std()), 2),
        "Min": round(float(s.min()), 2), "Q1": round(float(s.quantile(0.25)), 2),
        "Q3": round(float(s.quantile(0.75)), 2), "Max": round(float(s.max()), 2),
        "Skewness": round(float(s.skew()), 2),
    })
stats_df = pd.DataFrame(stats_rows)
stats_df.to_csv(REPORTS / "statistics_summary.csv", index=False)
pearson = cust_pos[corr_cols].corr(method="pearson").round(2)

# ==========================================================================
# KEY FINDINGS (all numbers computed above)
# ==========================================================================
k_all = dash["all"]["kpis"]
q4_10 = base[(base["Year"] == 2010) & (base["Month"] >= 9) & (base["Month"] <= 11)]["Revenue"].sum()
share_q4 = q4_10 / base[base["Year"] == 2010]["Revenue"].sum() * 100
guest_rev = base[~base["HasCustomerID"]]["Revenue"].sum() / base["Revenue"].sum() * 100
one_time = (cust["Frequency"] == 1).mean() * 100
nl_aov = dash["all"]["countries"]
nl_row = next(c for c in nl_aov if c["name"] == "Netherlands")
uk_row = next(c for c in nl_aov if c["name"] == "United Kingdom")
lowest = prod_all[prod_all["orders"] >= 20].sort_values("net_revenue").head(10)

findings = [
    {"title": "Strong Christmas seasonality",
     "text": f"September to November produced {share_q4:.1f}% of 2010 revenue. November is the top month in both "
             f"years ({gbp(m10.loc[11])} in 2010 and {gbp(m11.loc[11])} in 2011)."},
    {"title": "Stable year-on-year business",
     "text": f"Jan-Nov revenue moved from {gbp(jan_nov_10)} (2010) to {gbp(jan_nov_11)} (2011), a change of {yoy:+.1f}%."},
    {"title": "Heavy dependence on the UK",
     "text": f"The United Kingdom provides {uk_share:.1f}% of net revenue; {intl.index[0]}, {intl.index[1]} and "
             f"{intl.index[2]} are the largest export markets."},
    {"title": "Export customers place bigger orders",
     "text": f"Average order value in the Netherlands is {gbp(nl_row['aov'])} compared with {gbp(uk_row['aov'])} in the UK, "
             "showing that overseas buyers are mostly large wholesalers."},
    {"title": "80/20 customer pattern",
     "text": f"The top 20% of customers generate {top20_share:.1f}% of identified-customer revenue, while "
             f"{one_time:.1f}% of customers ordered only once."},
    {"title": "Long-tail product catalogue",
     "text": f"{k_all['products']:,} products were sold; the top 10 account for only {top10_share:.1f}% of revenue. "
             f"The best seller is '{top10.iloc[0]['Description'].title()}'."},
    {"title": "Cancellations are significant",
     "text": f"{k_all['cancellation_rate']:.1f}% of invoices are cancellations, removing {gbp(k_all['cancelled_value'])} "
             f"({k_all['cancellation_value_rate']:.1f}% of gross sales)."},
    {"title": "Weekday, office-hours business",
     "text": f"Sales peak on {day_rev.idxmax()} and at {hour_rev.idxmax()}:00; Saturday trading is almost zero, "
             "which fits a business-to-business wholesaler."},
    {"title": "Skewed order values",
     "text": f"The median order is {gbp(order_val.median())} but the mean is {gbp(order_val.mean())}; a small number "
             "of very large orders pull the average up."},
    {"title": "Missing customer IDs matter",
     "text": f"{clean['missing_customer_rows']:,} rows have no Customer ID; these rows still carry {guest_rev:.1f}% of net revenue, "
             "so customer-level results describe identified customers only."},
]

# ==========================================================================
# WRITE static/data.js  (loaded by the website with a normal <script> tag,
# so it works even when index.html is opened directly from the file system)
# ==========================================================================
site_data = {
    "generated": datetime.now().strftime("%d %b %Y, %H:%M"),
    "dataset": {
        "name": "Online Retail II",
        "source": "UCI Machine Learning Repository",
        "url": "https://archive.ics.uci.edu/dataset/502/online+retail+ii",
        "date_range": f"{df['InvoiceDate'].min():%d %b %Y} - {df['InvoiceDate'].max():%d %b %Y}",
        "raw_rows": clean["raw_profile"]["rows"],
        "clean_rows": clean["clean_profile"]["rows"],
        "raw_columns": clean["raw_profile"]["columns"],
        "clean_columns": clean["clean_profile"]["columns"],
        "sheets": clean["sheets"],
    },
    "cleaning": clean,
    "data_dictionary": pd.read_csv(REPORTS / "data_dictionary.csv").fillna("").to_dict(orient="records"),
    "before_after": pd.read_csv(REPORTS / "before_after_comparison.csv").fillna("").to_dict(orient="records"),
    "stats": stats_rows,
    "correlation": {"columns": corr_cols, "spearman": corr.values.tolist(), "pearson": pearson.values.tolist()},
    "periods": dash,
    "charts": charts,
    "findings": findings,
    "extra": {
        "yoy_jan_nov": round(yoy, 2), "jan_nov_2010": round(jan_nov_10, 2), "jan_nov_2011": round(jan_nov_11, 2),
        "uk_share": round(uk_share, 2), "top20_share": round(top20_share, 2), "one_time_pct": round(one_time, 2),
        "top10_share": round(top10_share, 2), "q4_share_2010": round(share_q4, 2),
        "peak_month": peak_m, "peak_month_revenue": round(float(monthly.max()), 2),
        "best_day": day_rev.idxmax(), "best_hour": int(hour_rev.idxmax()),
        "guest_revenue_share": round(guest_rev, 2),
        "lowest_products": [{"name": r.Description.title(), "revenue": round(r.net_revenue, 2), "orders": int(r.orders)}
                            for r in lowest.itertuples()],
        "most_cancelled": [{"name": n.title(), "value": round(v, 2)} for n, v in canc_plot.items()],
    },
}
OUT_JS.write_text("// Generated by analysis/exploratory_analysis.py - do not edit by hand\n"
                  "window.PROJECT_DATA = " + json.dumps(site_data, default=str) + ";\n", encoding="utf-8")

# Plain-text summary for the report
lines = ["EDA SUMMARY - Online Retail II", f"Generated: {site_data['generated']}", "", "KPIs (all data):"]
lines += [f"  {k:<24} {v:,}" if isinstance(v, int) else f"  {k:<24} {v:,.2f}" for k, v in k_all.items()]
lines += ["", "Descriptive statistics:", stats_df.to_string(index=False), "",
          "Spearman correlation (customer level):", corr.to_string(), "", "Key findings:"]
lines += [f"- {f['title']}: {f['text']}" for f in findings]
(REPORTS / "eda_summary.txt").write_text("\n".join(lines), encoding="utf-8")

n_charts = len(charts["cleaning"]) + len(charts["eda"]) + sum(len(v) for v in charts["dashboard"].values())
print(f"Saved {n_charts} Matplotlib charts and static/data.js")
print("Exploratory analysis finished successfully.")
