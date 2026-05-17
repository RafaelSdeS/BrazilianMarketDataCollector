#!/usr/bin/env python
# coding: utf-8

from pathlib import Path

import pandas as pd


DATA_PATH = Path("clean_data/final_data/df_principal.pkl")
REPORTS_DIR = Path("reports")
HTML_OUTPUT = REPORTS_DIR / "vale_petrobras_raw_data.html"
OPEN_TAB_OUTPUT = REPORTS_DIR / "vale_dashboard.html"
CSV_OUTPUT = REPORTS_DIR / "vale_petrobras_raw_data.csv"
TICKERS = ["VALE3", "PETR3", "PETR4"]


def load_raw_company_rows(tickers: list[str]) -> pd.DataFrame:
    df = pd.read_pickle(DATA_PATH)
    raw = df.loc[df["CODIGO"].isin(tickers)].copy()

    if raw.empty:
        raise ValueError(f"No rows found for tickers: {', '.join(tickers)}")

    raw["DT_FIM_EXERC"] = pd.to_datetime(raw["DT_FIM_EXERC"], errors="coerce")
    raw.sort_values(["CODIGO", "DT_FIM_EXERC", "LABEL"], inplace=True)

    return raw


def build_html_table(raw: pd.DataFrame) -> str:
    table = raw.to_html(index=False, border=0, classes="raw-table", na_rep="")
    tickers = ", ".join(TICKERS)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Raw collected data: Vale and Petrobras</title>
  <style>
    body {{
      margin: 0;
      font: 13px/1.35 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #111827;
      background: #f6f7f9;
    }}
    header {{
      padding: 18px 22px;
      background: #ffffff;
      border-bottom: 1px solid #d9dee8;
      position: sticky;
      top: 0;
      z-index: 3;
    }}
    h1 {{
      margin: 0;
      font-size: 20px;
      letter-spacing: 0;
    }}
    p {{
      margin: 6px 0 0;
      color: #4b5563;
    }}
    .wrap {{
      padding: 16px;
    }}
    .table-wrap {{
      overflow: auto;
      max-height: calc(100vh - 112px);
      border: 1px solid #d9dee8;
      background: white;
    }}
    table {{
      border-collapse: collapse;
      min-width: 100%;
      white-space: nowrap;
    }}
    th, td {{
      border: 1px solid #e5e7eb;
      padding: 6px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #eef2f7;
      position: sticky;
      top: 0;
      z-index: 2;
    }}
    td:first-child, th:first-child {{
      position: sticky;
      left: 0;
      background: #f8fafc;
      z-index: 1;
    }}
    th:first-child {{
      z-index: 4;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Raw collected data: Vale and Petrobras</h1>
    <p>Source: {DATA_PATH} | Tickers: {tickers} | Rows: {len(raw)} | Columns: {len(raw.columns)}</p>
  </header>
  <div class="wrap">
    <div class="table-wrap">
      {table}
    </div>
  </div>
</body>
</html>"""


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    raw = load_raw_company_rows(TICKERS)

    raw.to_csv(CSV_OUTPUT, index=False)
    html_table = build_html_table(raw)
    HTML_OUTPUT.write_text(html_table, encoding="utf-8")
    OPEN_TAB_OUTPUT.write_text(html_table, encoding="utf-8")

    print(f"Raw HTML table saved to {HTML_OUTPUT}")
    print(f"Raw HTML table also saved to {OPEN_TAB_OUTPUT}")
    print(f"Raw CSV saved to {CSV_OUTPUT}")


if __name__ == "__main__":
    main()
