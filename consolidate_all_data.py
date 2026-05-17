#!/usr/bin/env python3
"""
Consolidate all company data into a single CSV file.
Fetches dividend history and current prices from Yahoo Finance for all listed companies.

Output: all_companies_consolidated.csv containing:
- Company information (ticker, name, sector, segment, etc.)
- Current price
- TTM dividends and dividend yield
- Historical dividend totals
- Yearly dividend breakdown (2000-2026)
"""

import pandas as pd
import numpy as np
from yahooquery import Ticker
import datetime
from dateutil.relativedelta import relativedelta
import warnings
import time
import os

warnings.filterwarnings('ignore')


def normalize_ticker(symbol):
    return str(symbol).upper().replace('.SA', '')


def dividend_class(value):
    if pd.isna(value):
        return value
    value = str(value)
    if value.startswith('UNT'):
        return 'UNT'
    return value


def chunked(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def main():
    print("=" * 100)
    print("🚀 CONSOLIDATING ALL COMPANY DATA INTO SINGLE CSV")
    print("=" * 100)

    # ========================================================================
    # STEP 1: Load company information
    # ========================================================================
    print("\n📊 STEP 1: Loading company information...")
    
    companies_info = pd.read_excel('info_brazilian_companies.xlsx')
    print(f"   Found {len(companies_info)} companies in the database")
    
    all_tickers = companies_info['CODIGO'].dropna().unique().tolist()
    print(f"   Total tickers: {len(all_tickers)}")

    # ========================================================================
    # STEP 2: Fetch dividend and price data
    # ========================================================================
    print("\n📊 STEP 2: Fetching dividend data from Yahoo Finance...")
    print(f"   Processing {len(all_tickers)} tickers in batches of 25...")
    
    all_dividends = []
    all_prices = {}
    
    batch_num = 0
    total_batches = (len(all_tickers) + 24) // 25
    
    for batch in chunked(all_tickers, 25):
        batch_num += 1
        yahoo_symbols = [f'{t.lower()}.sa' for t in batch]
        
        print(f"   Batch {batch_num}/{total_batches}: {len(batch)} tickers...", end=" ", flush=True)
        
        try:
            # Fetch historical data
            history = Ticker(yahoo_symbols).history(period='max', interval='1d')
            
            if not isinstance(history, dict) and not history.empty:
                history = history.reset_index()
                
                if 'dividends' in history.columns:
                    div_rows = history[history['dividends'].fillna(0) > 0].copy()
                    if not div_rows.empty:
                        div_rows['CODIGO'] = div_rows['symbol'].map(normalize_ticker)
                        all_dividends.append(div_rows[['CODIGO', 'date', 'dividends']])
            
            # Fetch current prices
            price_data = Ticker(yahoo_symbols).price
            if isinstance(price_data, dict):
                for symbol, data in price_data.items():
                    if isinstance(data, dict) and data.get('regularMarketPrice'):
                        all_prices[normalize_ticker(symbol)] = data['regularMarketPrice']
            
            print(f"✓ ({len(all_prices)} prices collected)")
            
        except Exception as e:
            print(f"⚠ Error: {str(e)[:50]}")
        
        time.sleep(0.5)

    # Combine dividends
    if all_dividends:
        dividends_df = pd.concat(all_dividends, ignore_index=True)
        dividends_df['Data COM'] = pd.to_datetime(dividends_df['date'], utc=True).dt.tz_localize(None)
        dividends_df['Valor ajustado'] = dividends_df['dividends'].astype(float)
        dividends_df['ano'] = dividends_df['Data COM'].dt.year
        print(f"\n   ✅ Total dividend records: {len(dividends_df)}")
    else:
        dividends_df = pd.DataFrame()
        print("\n   ⚠ No dividend data collected")
    
    print(f"   ✅ Total prices collected: {len(all_prices)}")

    # ========================================================================
    # STEP 3: Calculate aggregations
    # ========================================================================
    print("\n📊 STEP 3: Calculating dividend aggregations...")
    
    today = datetime.datetime.today()
    one_year_ago = (today - relativedelta(years=1)).strftime('%Y-%m-%d')
    
    company_map = companies_info[['CODIGO', 'CD_CVM', 'CLASSE']].copy()
    company_map['CLASSE'] = company_map['CLASSE'].map(dividend_class)
    
    if not dividends_df.empty:
        dividends_df = dividends_df.merge(company_map, on='CODIGO', how='left')
        dividends_df.dropna(subset=['CD_CVM', 'CLASSE', 'Valor ajustado'], inplace=True)
        
        # Yearly dividends
        dv_year = dividends_df.groupby(['CODIGO', 'ano'], as_index=False)['Valor ajustado'].sum()
        dv_year.rename(columns={'Valor ajustado': 'Dividendos_Ano', 'ano': 'Ano'}, inplace=True)
        
        # TTM dividends
        ttm_mask = dividends_df['Data COM'] >= one_year_ago
        dv_ttm = dividends_df[ttm_mask].groupby('CODIGO', as_index=False)['Valor ajustado'].sum()
        dv_ttm.rename(columns={'Valor ajustado': 'Dividendos_TTM'}, inplace=True)
        
        # Total dividends
        dv_total = dividends_df.groupby('CODIGO', as_index=False).agg({
            'Valor ajustado': 'sum',
            'Data COM': ['min', 'max', 'count']
        })
        dv_total.columns = ['CODIGO', 'Dividendos_Total', 'Primeiro_Dividendo', 'Ultimo_Dividendo', 'Total_Pagamentos']
        
        print(f"   ✅ Yearly records: {len(dv_year)}")
        print(f"   ✅ TTM records: {len(dv_ttm)}")
    else:
        dv_year = pd.DataFrame()
        dv_ttm = pd.DataFrame()
        dv_total = pd.DataFrame()

    # ========================================================================
    # STEP 4: Create consolidated dataframe
    # ========================================================================
    print("\n📊 STEP 4: Creating consolidated dataframe...")
    
    consolidated = companies_info.copy()
    consolidated['Preco_Atual'] = consolidated['CODIGO'].map(all_prices)
    
    if not dv_ttm.empty:
        consolidated = consolidated.merge(dv_ttm, on='CODIGO', how='left')
    else:
        consolidated['Dividendos_TTM'] = np.nan
    
    if not dv_total.empty:
        consolidated = consolidated.merge(dv_total, on='CODIGO', how='left')
    else:
        consolidated['Dividendos_Total'] = np.nan
        consolidated['Primeiro_Dividendo'] = np.nan
        consolidated['Ultimo_Dividendo'] = np.nan
        consolidated['Total_Pagamentos'] = np.nan
    
    consolidated['Dividend_Yield_TTM'] = consolidated['Dividendos_TTM'] / consolidated['Preco_Atual']
    consolidated['Dividend_Yield_TTM_Pct'] = consolidated['Dividend_Yield_TTM'] * 100

    # ========================================================================
    # STEP 5: Add yearly dividend columns
    # ========================================================================
    print("\n📊 STEP 5: Creating yearly dividend pivot...")
    
    if not dv_year.empty:
        yearly_pivot = dv_year.pivot(index='CODIGO', columns='Ano', values='Dividendos_Ano')
        yearly_pivot.columns = [f'Div_{int(year)}' for year in yearly_pivot.columns]
        yearly_pivot = yearly_pivot.reset_index()
        consolidated = consolidated.merge(yearly_pivot, on='CODIGO', how='left')

    # ========================================================================
    # STEP 6: Reorder columns
    # ========================================================================
    print("\n📊 STEP 6: Organizing columns...")
    
    priority_cols = [
        'CODIGO', 'NAME_PREG', 'DENOM_SOCIAL', 'CLASSE', 'CD_CVM',
        'SETOR', 'SUBSETOR', 'SEGMENTO', 'SEGMENTO_B3',
        'Preco_Atual', 'Dividendos_TTM', 'Dividend_Yield_TTM_Pct',
        'Dividendos_Total', 'Total_Pagamentos', 'Primeiro_Dividendo', 'Ultimo_Dividendo'
    ]
    
    yearly_cols = sorted([c for c in consolidated.columns if c.startswith('Div_')])
    other_cols = [c for c in consolidated.columns if c not in priority_cols and c not in yearly_cols]
    
    final_cols = [c for c in priority_cols if c in consolidated.columns] + yearly_cols + other_cols
    consolidated = consolidated[[c for c in final_cols if c in consolidated.columns]]

    # ========================================================================
    # STEP 7: Save to CSV
    # ========================================================================
    print("\n📊 STEP 7: Saving to CSV...")
    
    output_file = 'all_companies_consolidated.csv'
    consolidated.to_csv(output_file, index=False)
    
    print(f"\n{'=' * 100}")
    print(f"✅ CONSOLIDATED DATA SAVED TO: {output_file}")
    print(f"{'=' * 100}")
    print(f"\n📊 Summary:")
    print(f"   • Total companies: {len(consolidated)}")
    print(f"   • Total columns: {len(consolidated.columns)}")
    print(f"   • Companies with price data: {consolidated['Preco_Atual'].notna().sum()}")
    print(f"   • Companies with dividend data: {consolidated['Dividendos_TTM'].notna().sum()}")
    print(f"   • Yearly dividend columns: {len(yearly_cols)}")
    print(f"   • Data fetched on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return consolidated


if __name__ == '__main__':
    main()
