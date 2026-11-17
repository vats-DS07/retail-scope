# RetailScope — Online Retail II Data Cleaning & Visualization

A **Foundation of Data Science** capstone project. Over one million real transactions from a UK online
gift wholesaler (UCI *Online Retail II*, Dec 2009 – Dec 2011) are cleaned with **Pandas**, analysed with
descriptive statistics and visualised with **Matplotlib**. The results are presented in a dark-themed static
website built with **HTML, CSS and vanilla JavaScript**.

## Highlights

| | |
|---|---|
| Original data | 1,067,371 rows × 8 columns (2 Excel sheets) |
| Cleaned data | 1,033,036 rows × 21 columns |
| Net product revenue | £18.93M (gross sales £19.64M minus £0.72M cancellations) |
| Orders / customers / countries | 39,516 / 5,852 / 43 |
| Charts | 40 Matplotlib PNGs (3 cleaning, 13 EDA, 8 dashboard charts × 3 periods) |

Key cleaning decisions:
- The two Excel sheets **overlap** (1–9 Dec 2010). 22,523 identical rows were removed so that period is not counted twice.
- 11,812 exact duplicate rows were removed.
- Negative quantities were **not deleted blindly**. Every row is classified as Sale, Cancellation (`C` invoices,
  kept as negative revenue), Stock Adjustment, Zero-Price Entry or Bad Debt Adjustment.
- Missing Customer IDs (22.8%) were kept and flagged, and never invented.
- Outliers were flagged with the IQR rule and kept, because large wholesale orders are genuine.

## Tech stack

Python 3 · Pandas · Matplotlib · openpyxl (Excel reader) · HTML5 · CSS3 · vanilla JavaScript.
The project doesn't use NumPy imports, Seaborn, Plotly, any web framework or any JS chart library.

## Project structure

```
Ecommerce_Data_Analysis/
├── index.html                  # redirects to static/index.html (clean GitHub Pages URL)
├── main.py                     # runs the full pipeline (and an optional local server)
├── requirements.txt
├── analysis/
│   ├── data_cleaning.py        # cleaning + reports
│   └── exploratory_analysis.py # statistics, Matplotlib charts, static/data.js
├── dataset/
│   ├── original_dataset.xlsx   # untouched original
│   ├── cleaned_dataset.csv     # full cleaned data (local only, ~160 MB)
│   └── cleaned_dataset.csv.gz  # compressed copy committed to GitHub
├── reports/
│   ├── cleaning_summary.txt
│   ├── cleaning_report.json
│   ├── data_dictionary.csv
│   ├── before_after_comparison.csv
│   ├── statistics_summary.csv
│   └── eda_summary.txt
├── visualizations/
│   ├── cleaning/   # charts for the Data Cleaning page
│   ├── eda/        # charts for the EDA page
│   └── dashboard/  # all_*, 2010_*, 2011_* charts for the dashboard filter
└── static/
    ├── index.html  style.css  script.js
    ├── data.js     # numbers produced by Python for the website
    ├── assets/favicon.svg
    └── fonts/      # Inter (SIL Open Font License)
```

## Run it locally

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

python main.py                   # cleaning + EDA + charts (about 2 minutes)
python main.py --serve-only      # open the website at http://localhost:8000
```

You can also open `index.html` directly in a browser. The site reads `static/data.js` with a normal
`<script>` tag, so it works without a server.

## Website pages

1. **Overview**: objectives, dataset facts, workflow.
2. **Data Cleaning**: missing values, duplicates, data types, all cleaning steps, before/after table, data dictionary.
3. **Exploratory Analysis**: statistical summary, 13 charts with topic filters, Pearson/Spearman correlation table.
4. **Dashboard**: KPI cards and charts with an All / 2010 / 2011 filter, product search, sorting, side-by-side product comparison, country search, monthly table.
5. **Insights**: findings generated from the results, recommendations, limitations, conclusion.
6. **About**: description, technologies, dataset citation, methodology, student details.

## Dataset

Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C5CG6D — licensed under CC BY 4.0.

## Student

[Your Name] · [Roll Number] · BCA AI & Data Science · Foundation of Data Science · Mentor: [Mentor Name]
"# retail-scope" 
