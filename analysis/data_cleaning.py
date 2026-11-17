"""
data_cleaning.py
================
Foundation of Data Science - Capstone Project
Online Retail II (UCI) : Data Cleaning and Preprocessing

What this script does
---------------------
1.  Loads BOTH sheets of the original Excel file (the original is never modified).
2.  Inspects structure, column names, data types, missing values and duplicates.
3.  Finds inconsistent values, negative quantities, cancelled invoices and outliers.
4.  Cleans the data step by step and records every decision in a cleaning log.
5.  Creates derived columns (Revenue, Year, Month, TransactionType ...).
6.  Exports:
        dataset/cleaned_dataset.csv            (full cleaned data)
        dataset/cleaned_dataset.csv.gz         (compressed copy for GitHub)
        reports/cleaning_report.json           (numbers used by the website)
        reports/cleaning_summary.txt           (human-readable summary)
        reports/data_dictionary.csv            (column descriptions)
        reports/before_after_comparison.csv    (before vs after statistics)

Libraries used: pandas + Python standard library only.

Run from the project root:
    python analysis/data_cleaning.py
"""

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Paths (relative to the project root, so the project works on any computer)
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = ROOT / "dataset" / "original_dataset.xlsx"
CLEAN_CSV = ROOT / "dataset" / "cleaned_dataset.csv"
CLEAN_GZ = ROOT / "dataset" / "cleaned_dataset.csv.gz"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)

# Stock codes that are NOT physical products (postage, fees, manual entries,
# discounts, samples, test codes, gift vouchers). Identified by inspecting the
# list of stock codes that do not follow the normal 5-digit product pattern.
NON_PRODUCT_PATTERN = (
    r"^(POST|DOT|M|C2|D|S|B|PADS|CRUK|AMAZONFEE|BANK CHARGES|ADJUST\d*|TEST\d*|GIFT_.*)$"
)

# Country names written inconsistently in the source data
COUNTRY_FIXES = {
    "EIRE": "Ireland",
    "RSA": "South Africa",
    "USA": "United States",
}

log = []  # every cleaning step is appended here as a dictionary


def section(title):
    """Print a clear heading in the terminal output."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def record(step, action, rows_before, rows_after, reason):
    """Store one cleaning step in the log (this becomes the cleaning summary)."""
    entry = {
        "step": step,
        "action": action,
        "rows_before": int(rows_before),
        "rows_after": int(rows_after),
        "rows_changed": int(rows_before - rows_after),
        "reason": reason,
    }
    log.append(entry)
    print(f"[{step}] {action}: {rows_before:,} -> {rows_after:,} rows")


def basic_profile(df):
    """Small set of statistics used for the before-and-after comparison."""
    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "missing_description": int(df["Description"].isna().sum()),
        "missing_customer_id": int(df["Customer ID"].isna().sum())
        if "Customer ID" in df
        else int(df["CustomerID"].isna().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "negative_quantity_rows": int((df["Quantity"] < 0).sum()),
        "zero_or_negative_price_rows": int((df["Price"] <= 0).sum()),
        "unique_invoices": int(df["Invoice"].nunique()),
        "unique_stock_codes": int(df["StockCode"].nunique()),
        "unique_countries": int(df["Country"].nunique()),
        "quantity_min": float(df["Quantity"].min()),
        "quantity_max": float(df["Quantity"].max()),
        "price_min": float(df["Price"].min()),
        "price_max": float(df["Price"].max()),
    }


def iqr_bounds(series):
    """Return (lower, upper) limits using the 1.5 x IQR rule."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def main():
    # ======================================================================
    # STEP 1 - LOAD THE ORIGINAL DATASET (both sheets)
    # ======================================================================
    section("STEP 1: Loading the original dataset")
    print(f"Reading {RAW_FILE.name} ... (this takes about a minute)")
    sheets = pd.read_excel(RAW_FILE, sheet_name=None)  # dict: sheet name -> DataFrame
    sheet_info = {}
    for name, sheet in sheets.items():
        sheet["SourceSheet"] = name
        sheet_info[name] = {
            "rows": int(len(sheet)),
            "start": str(sheet["InvoiceDate"].min()),
            "end": str(sheet["InvoiceDate"].max()),
        }
        print(f"  {name}: {len(sheet):,} rows, "
              f"{sheet['InvoiceDate'].min()} to {sheet['InvoiceDate'].max()}")

    raw = pd.concat(sheets.values(), ignore_index=True)
    raw_profile = basic_profile(raw.drop(columns="SourceSheet"))

    # ======================================================================
    # STEP 2 - INSPECT STRUCTURE
    # ======================================================================
    section("STEP 2: Inspecting the structure")
    print(f"Rows: {raw.shape[0]:,}   Columns: {raw.shape[1] - 1} (+ SourceSheet helper)")
    print("\nColumn names and data types:")
    dtypes_raw = {col: str(raw[col].dtype) for col in raw.columns if col != "SourceSheet"}
    for col, dt in dtypes_raw.items():
        print(f"  {col:<12} {dt}")
    print("\nFirst five rows:")
    print(raw.head().to_string())

    # ======================================================================
    # STEP 3 - MISSING VALUES
    # ======================================================================
    section("STEP 3: Missing values")
    missing = raw.drop(columns="SourceSheet").isna().sum()
    missing_pct = (missing / len(raw) * 100).round(2)
    missing_table = pd.DataFrame({"missing": missing, "percent": missing_pct})
    print(missing_table.to_string())

    # ======================================================================
    # STEP 4 - REMOVE THE OVERLAP BETWEEN THE TWO SHEETS
    # ======================================================================
    # Sheet "Year 2009-2010" runs until 09-Dec-2010, while sheet "Year 2010-2011"
    # starts on 01-Dec-2010. The rows for 01-09 Dec 2010 therefore appear in both
    # sheets. We keep them only once (from the 2010-2011 sheet).
    section("STEP 4: Removing rows repeated in both sheets")
    first, second = list(sheets.keys())
    overlap_start = sheets[second]["InvoiceDate"].min().normalize()
    overlap_mask = (raw["SourceSheet"] == first) & (raw["InvoiceDate"] >= overlap_start)
    overlap_rows = int(overlap_mask.sum())
    # Safety check: the overlapping rows must really be identical in both sheets
    a = raw[overlap_mask].drop(columns="SourceSheet").fillna("NA")
    b = raw[(raw["SourceSheet"] == second) & (raw["InvoiceDate"] < sheets[first]["InvoiceDate"].max().normalize() + pd.Timedelta(days=1))]
    b = b.drop(columns="SourceSheet").fillna("NA")
    sort_cols = list(a.columns)
    identical = a.sort_values(sort_cols).reset_index(drop=True).equals(
        b.sort_values(sort_cols).reset_index(drop=True)
    )
    print(f"Overlap period starts {overlap_start.date()}; rows in first sheet: {overlap_rows:,}; "
          f"identical to second sheet: {identical}")
    before = len(raw)
    df = raw[~overlap_mask].copy()
    record("4", "Removed sheet-overlap rows (1-9 Dec 2010)", before, len(df),
           "Both Excel sheets contain the same transactions for 1-9 December 2010 "
           "(verified identical). Keeping both copies would double-count that period.")

    # ======================================================================
    # STEP 5 - DUPLICATE RECORDS
    # ======================================================================
    section("STEP 5: Duplicate records")
    cols_no_sheet = [c for c in df.columns if c != "SourceSheet"]
    dup_mask = df.duplicated(subset=cols_no_sheet, keep="first")
    print(f"Exact duplicate rows (all 8 columns identical): {dup_mask.sum():,}")
    print(df[df.duplicated(subset=cols_no_sheet, keep=False)].head(6).to_string())
    before = len(df)
    df = df[~dup_mask].copy()
    record("5", "Removed exact duplicate rows", before, len(df),
           "Rows identical in every column (same invoice, product, quantity, price, "
           "timestamp and customer) are treated as accidental double entries.")

    # ======================================================================
    # STEP 6 - RENAME COLUMNS AND CORRECT DATA TYPES
    # ======================================================================
    section("STEP 6: Correcting column names and data types")
    df = df.rename(columns={"Customer ID": "CustomerID"})
    df["Invoice"] = df["Invoice"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()
    df["Country"] = df["Country"].astype(str).str.strip()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Quantity"] = df["Quantity"].astype("int64")
    df["Price"] = df["Price"].astype("float64")
    # Customer ID is read as a float (e.g. 13085.0) because of missing values.
    # It is an identifier, not a number, so convert it to a whole-number string.
    df["CustomerID"] = df["CustomerID"].astype("Int64").astype("string")
    for col in ["Invoice", "StockCode", "Country", "CustomerID", "InvoiceDate"]:
        print(f"  {col:<12} -> {df[col].dtype}")
    record("6", "Standardised column names and data types", len(df), len(df),
           "CustomerID converted from float (13085.0) to text ID (13085); Invoice and "
           "StockCode stored as text; StockCode upper-cased (e.g. 'm' -> 'M').")

    # ======================================================================
    # STEP 7 - INCONSISTENT VALUES
    # ======================================================================
    section("STEP 7: Inconsistent values")
    # 7a. Country names
    country_counts = {k: int((df["Country"] == k).sum()) for k in COUNTRY_FIXES}
    df["Country"] = df["Country"].replace(COUNTRY_FIXES)
    print("Country names standardised:", country_counts)
    record("7a", "Standardised country names", len(df), len(df),
           "EIRE -> Ireland, RSA -> South Africa, USA -> United States "
           f"({sum(country_counts.values()):,} rows). 'Unspecified' kept as-is.")

    # 7b. Descriptions: extra spaces and several spellings for one product
    df["Description"] = (
        df["Description"].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    )
    variants = (
        df[df["Price"] > 0].groupby("StockCode")["Description"].nunique()
    )
    multi_desc_codes = int((variants > 1).sum())
    # The most common description among real sales becomes the standard name
    standard_name = (
        df[(df["Price"] > 0) & df["Description"].notna()]
        .groupby("StockCode")["Description"]
        .agg(lambda s: s.value_counts().index[0])
    )
    missing_desc_before = int(df["Description"].isna().sum())
    mapped = df["StockCode"].map(standard_name)
    # Only priced rows are renamed. On zero-price rows the text is often a staff
    # note ("damaged", "given away") which is useful information, so it is kept.
    rename_mask = (df["Price"] > 0) & mapped.notna() & (mapped != df["Description"])
    changed = int(rename_mask.sum())
    df.loc[rename_mask, "Description"] = mapped[rename_mask]
    fill_mask = df["Description"].isna() & mapped.notna()
    df.loc[fill_mask, "Description"] = mapped[fill_mask]
    filled = int(fill_mask.sum())
    df["Description"] = df["Description"].fillna("UNKNOWN")
    print(f"Stock codes with more than one description: {multi_desc_codes:,}")
    print(f"Rows whose description was standardised: {changed:,}")
    print(f"Missing descriptions filled from the same StockCode: {filled:,}; "
          f"left as 'UNKNOWN': {missing_desc_before - filled:,}")
    record("7b", "Standardised product descriptions", len(df), len(df),
           f"{multi_desc_codes:,} stock codes had several spellings; each now uses its most "
           f"frequent sales description. {filled:,} missing descriptions were filled from the "
           f"same StockCode (not invented); {missing_desc_before - filled:,} with no match "
           "were labelled 'UNKNOWN'.")

    # ======================================================================
    # STEP 8 - NEGATIVE QUANTITIES, CANCELLATIONS AND ADJUSTMENTS
    # ======================================================================
    section("STEP 8: Negative quantities, cancelled invoices and adjustments")
    is_cancel = df["Invoice"].str.startswith("C")
    is_baddebt = df["Invoice"].str.startswith("A")
    neg_qty = df["Quantity"] < 0
    print(f"Rows with negative quantity: {neg_qty.sum():,}")
    print(f"  of which cancellation invoices ('C' prefix): {(neg_qty & is_cancel).sum():,}")
    print(f"  of which NOT cancellations (stock write-offs, price 0): "
          f"{(neg_qty & ~is_cancel).sum():,}")
    print(f"Cancellation invoices: {df.loc[is_cancel, 'Invoice'].nunique():,} "
          f"({is_cancel.sum():,} rows)")
    print(f"Bad-debt adjustment invoices ('A' prefix): {is_baddebt.sum():,} rows")
    print("Most common notes on non-cancellation negative rows:")
    print(df.loc[neg_qty & ~is_cancel, "Description"].value_counts().head(8).to_string())

    df["IsProduct"] = ~df["StockCode"].str.match(NON_PRODUCT_PATTERN, case=False)

    # Classify every row instead of deleting it
    df["TransactionType"] = "Sale"
    df.loc[(df["Price"] == 0) & ~is_cancel, "TransactionType"] = "Zero-Price Entry"
    df.loc[neg_qty & ~is_cancel, "TransactionType"] = "Stock Adjustment"
    df.loc[is_cancel, "TransactionType"] = "Cancellation"
    df.loc[is_baddebt, "TransactionType"] = "Bad Debt Adjustment"
    df["IsCancelled"] = is_cancel
    print("\nTransaction types:")
    print(df["TransactionType"].value_counts().to_string())
    print(f"\nNon-product rows (postage, fees, manual entries...): {(~df['IsProduct']).sum():,}")
    record("8", "Classified rows into transaction types (no rows deleted)", len(df), len(df),
           "Negative quantities were NOT blindly deleted. 'C' invoices are cancellations/returns "
           "and are kept as negative revenue so they offset the original sale. Negative rows with "
           "price 0 are internal stock write-offs (damaged, lost). 'A' invoices are bad-debt "
           "accounting entries. Postage, fees and manual codes are flagged IsProduct = False.")

    # ======================================================================
    # STEP 9 - DERIVED COLUMNS
    # ======================================================================
    section("STEP 9: Derived columns")
    df["Revenue"] = (df["Quantity"] * df["Price"]).round(2)
    df["Year"] = df["InvoiceDate"].dt.year
    df["Month"] = df["InvoiceDate"].dt.month
    df["YearMonth"] = df["InvoiceDate"].dt.strftime("%Y-%m")
    df["Quarter"] = df["InvoiceDate"].dt.year.astype(str) + "-Q" + df["InvoiceDate"].dt.quarter.astype(str)
    df["DayOfWeek"] = df["InvoiceDate"].dt.day_name()
    df["Hour"] = df["InvoiceDate"].dt.hour
    df["HasCustomerID"] = df["CustomerID"].notna()
    print("Added: Revenue, Year, Month, YearMonth, Quarter, DayOfWeek, Hour, HasCustomerID")
    record("9", "Created derived columns", len(df), len(df),
           "Revenue = Quantity x Price (negative for cancellations). Date parts allow monthly, "
           "weekday and hourly analysis.")

    # ======================================================================
    # STEP 10 - MISSING CUSTOMER IDs
    # ======================================================================
    section("STEP 10: Missing Customer IDs")
    miss_cust = int((~df["HasCustomerID"]).sum())
    miss_cust_rev = float(df.loc[~df["HasCustomerID"] & (df["TransactionType"] == "Sale"), "Revenue"].sum())
    print(f"Rows without CustomerID: {miss_cust:,} ({miss_cust / len(df) * 100:.1f}%)")
    print(f"Sales revenue on those rows: £{miss_cust_rev:,.0f}")
    record("10", "Kept rows with missing CustomerID (flagged)", len(df), len(df),
           f"{miss_cust:,} rows have no CustomerID (guest or unrecorded purchases). They are real "
           "sales, so they stay in revenue, product and country analysis but are excluded from "
           "customer-level analysis. No IDs were invented.")

    # ======================================================================
    # STEP 11 - OUTLIERS (IQR method)
    # ======================================================================
    section("STEP 11: Outlier detection")
    sales = df[(df["TransactionType"] == "Sale") & df["IsProduct"]]
    q_low, q_high = iqr_bounds(sales["Quantity"])
    p_low, p_high = iqr_bounds(sales["Price"])
    df["QuantityOutlier"] = False
    df["PriceOutlier"] = False
    sale_idx = sales.index
    df.loc[sale_idx, "QuantityOutlier"] = (sales["Quantity"] > q_high) | (sales["Quantity"] < q_low)
    df.loc[sale_idx, "PriceOutlier"] = (sales["Price"] > p_high) | (sales["Price"] < p_low)
    q_out = int(df["QuantityOutlier"].sum())
    p_out = int(df["PriceOutlier"].sum())
    print(f"Quantity IQR upper limit: {q_high:.1f} units -> {q_out:,} outlier sale lines")
    print(f"Price IQR upper limit: £{p_high:.2f} -> {p_out:,} outlier sale lines")
    extreme = df[df["Quantity"].abs() >= 70000][["Invoice", "StockCode", "Description",
                                                  "Quantity", "InvoiceDate", "CustomerID"]]
    print("\nExtreme quantities (each sale was cancelled minutes later):")
    print(extreme.to_string())
    record("11", "Flagged outliers with the IQR rule (kept, not deleted)", len(df), len(df),
           f"Quantity > {q_high:.0f} units flags {q_out:,} sale lines; price > £{p_high:.2f} flags "
           f"{p_out:,}. This is a wholesale business, so large orders are genuine and are kept. The "
           "two extreme orders (80,995 and 74,215 units) were each cancelled the same day; because "
           "cancellations are kept as negative revenue they cancel out in net figures.")

    # ======================================================================
    # STEP 12 - FINAL COLUMN ORDER AND EXPORT
    # ======================================================================
    section("STEP 12: Exporting the cleaned dataset")
    df = df.sort_values(["InvoiceDate", "Invoice"]).reset_index(drop=True)
    final_cols = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price",
                  "CustomerID", "Country", "Revenue", "TransactionType", "IsCancelled",
                  "IsProduct", "HasCustomerID", "QuantityOutlier", "PriceOutlier",
                  "Year", "Month", "YearMonth", "Quarter", "DayOfWeek", "Hour"]
    df = df[final_cols]
    df.to_csv(CLEAN_CSV, index=False)
    df.to_csv(CLEAN_GZ, index=False, compression="gzip")
    size_csv = CLEAN_CSV.stat().st_size / 1e6
    size_gz = CLEAN_GZ.stat().st_size / 1e6
    print(f"Saved {CLEAN_CSV.name} ({size_csv:.1f} MB) and {CLEAN_GZ.name} ({size_gz:.1f} MB)")

    # ======================================================================
    # REPORTS: before/after comparison, data dictionary, summary
    # ======================================================================
    clean_profile = basic_profile(df)
    labels = {
        "rows": "Total rows",
        "columns": "Columns",
        "missing_description": "Missing descriptions",
        "missing_customer_id": "Missing Customer IDs",
        "duplicate_rows": "Duplicate rows",
        "negative_quantity_rows": "Negative-quantity rows",
        "zero_or_negative_price_rows": "Zero/negative price rows",
        "unique_invoices": "Unique invoices",
        "unique_stock_codes": "Unique stock codes",
        "unique_countries": "Unique countries",
        "quantity_min": "Minimum quantity",
        "quantity_max": "Maximum quantity",
        "price_min": "Minimum price (£)",
        "price_max": "Maximum price (£)",
    }
    comparison = pd.DataFrame({
        "Metric": [labels[k] for k in raw_profile],
        "Before": [raw_profile[k] for k in raw_profile],
        "After": [clean_profile[k] for k in raw_profile],
    })
    comparison["Note"] = ""
    comparison.loc[comparison["Metric"] == "Negative-quantity rows", "Note"] = "Kept and classified, not deleted"
    comparison.loc[comparison["Metric"] == "Missing Customer IDs", "Note"] = "Kept and flagged (HasCustomerID)"
    comparison.loc[comparison["Metric"] == "Columns", "Note"] = "13 derived/flag columns added"
    comparison.loc[comparison["Metric"] == "Unique countries", "Note"] = "EIRE, RSA, USA renamed to full names"
    comparison.loc[comparison["Metric"] == "Unique stock codes", "Note"] = "Lower/upper-case variants merged"
    comparison.loc[comparison["Metric"] == "Duplicate rows", "Note"] = "Remaining rows differed only by description spelling"
    comparison.loc[comparison["Metric"] == "Missing descriptions", "Note"] = "Filled from same StockCode or 'UNKNOWN'"
    comparison.loc[comparison["Metric"] == "Total rows", "Note"] = "Sheet overlap and exact duplicates removed"
    comparison.to_csv(REPORT_DIR / "before_after_comparison.csv", index=False)
    print("\nBefore vs after:")
    print(comparison.to_string(index=False))

    dictionary = [
        ("Invoice", "text", "Original", "Invoice number. Prefix 'C' = cancellation, 'A' = bad-debt adjustment."),
        ("StockCode", "text", "Original (upper-cased)", "Product code."),
        ("Description", "text", "Original (standardised)", "Product name; most frequent spelling per StockCode."),
        ("Quantity", "integer", "Original", "Units per line. Negative for cancellations and stock write-offs."),
        ("InvoiceDate", "datetime", "Original", "Date and time of the transaction."),
        ("Price", "decimal (£)", "Original", "Unit price in pounds sterling."),
        ("CustomerID", "text", "Original (converted)", "Customer identifier; blank when not recorded."),
        ("Country", "text", "Original (standardised)", "Customer's country."),
        ("Revenue", "decimal (£)", "Derived", "Quantity x Price. Negative for cancellations."),
        ("TransactionType", "text", "Derived", "Sale, Cancellation, Stock Adjustment, Zero-Price Entry or Bad Debt Adjustment."),
        ("IsCancelled", "boolean", "Derived", "True when the invoice starts with 'C'."),
        ("IsProduct", "boolean", "Derived", "False for postage, fees, manual entries, discounts, samples, test codes."),
        ("HasCustomerID", "boolean", "Derived", "True when CustomerID is present."),
        ("QuantityOutlier", "boolean", "Derived", f"Product sale line with Quantity above the IQR limit ({q_high:.0f})."),
        ("PriceOutlier", "boolean", "Derived", f"Product sale line with Price above the IQR limit (£{p_high:.2f})."),
        ("Year", "integer", "Derived", "Year of InvoiceDate."),
        ("Month", "integer", "Derived", "Month number (1-12)."),
        ("YearMonth", "text", "Derived", "Year and month, e.g. 2011-11."),
        ("Quarter", "text", "Derived", "Year and quarter, e.g. 2011-Q4."),
        ("DayOfWeek", "text", "Derived", "Weekday name."),
        ("Hour", "integer", "Derived", "Hour of the day (0-23)."),
    ]
    dd = pd.DataFrame(dictionary, columns=["Column", "Type", "Source", "Description"])
    dd["Example"] = [str(df[c].iloc[0]) for c in dd["Column"]]
    dd["Missing"] = [int(df[c].isna().sum()) for c in dd["Column"]]
    dd.to_csv(REPORT_DIR / "data_dictionary.csv", index=False)

    type_counts = df["TransactionType"].value_counts()
    report = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_file": RAW_FILE.name,
        "sheets": sheet_info,
        "raw_profile": raw_profile,
        "clean_profile": clean_profile,
        "raw_dtypes": dtypes_raw,
        "clean_dtypes": {c: str(df[c].dtype) for c in df.columns},
        "missing_raw": {c: {"missing": int(missing[c]), "percent": float(missing_pct[c])} for c in missing.index},
        "overlap_rows_removed": overlap_rows,
        "overlap_identical": bool(identical),
        "duplicates_removed": int(dup_mask.sum()),
        "country_fixes": country_counts,
        "multi_description_codes": multi_desc_codes,
        "descriptions_standardised": changed,
        "descriptions_filled": filled,
        "descriptions_unknown": missing_desc_before - filled,
        "transaction_types": {k: int(v) for k, v in type_counts.items()},
        "cancellation_rows": int(df["IsCancelled"].sum()),
        "cancellation_invoices": int(df.loc[df["IsCancelled"], "Invoice"].nunique()),
        "non_product_rows": int((~df["IsProduct"]).sum()),
        "missing_customer_rows": miss_cust,
        "missing_customer_sales_revenue": round(miss_cust_rev, 2),
        "quantity_iqr_upper": float(q_high),
        "price_iqr_upper": round(float(p_high), 2),
        "quantity_outliers": q_out,
        "price_outliers": p_out,
        "csv_size_mb": round(size_csv, 1),
        "gz_size_mb": round(size_gz, 1),
        "steps": log,
    }
    with open(REPORT_DIR / "cleaning_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    lines = [
        "CLEANING SUMMARY - Online Retail II",
        f"Generated: {report['generated']}",
        "",
        f"Original rows (both sheets): {raw_profile['rows']:,}",
        f"Cleaned rows:                {clean_profile['rows']:,}",
        f"Rows removed:                {raw_profile['rows'] - clean_profile['rows']:,} "
        f"(overlap {overlap_rows:,} + duplicates {int(dup_mask.sum()):,})",
        "",
        "Transaction types in the cleaned data:",
    ]
    lines += [f"  {k:<22} {v:>9,}" for k, v in type_counts.items()]
    lines += ["", "Cleaning steps:"]
    for e in log:
        lines.append(f"\n[{e['step']}] {e['action']}  ({e['rows_before']:,} -> {e['rows_after']:,})")
        lines.append(f"    {e['reason']}")
    (REPORT_DIR / "cleaning_summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\nReports written to the reports/ folder.")
    print("Data cleaning finished successfully.")


if __name__ == "__main__":
    main()
