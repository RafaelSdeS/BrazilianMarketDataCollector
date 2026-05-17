#!/usr/bin/env python3
"""
Show complete dividend history for Vale, Petrobras, and Banco do Brasil.
Displays each individual dividend payment in the time series.
"""

import pandas as pd
import numpy as np
from yahooquery import Ticker
import datetime
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings('ignore')


def normalize_ticker(symbol):
    return str(symbol).upper().replace('.SA', '')


def main():
    print("=" * 90)
    print("📊 COMPLETE DIVIDEND HISTORY - VALE, PETROBRAS & BANCO DO BRASIL")
    print("=" * 90)
    
    # Target tickers
    tickers = {
        'BBAS3': 'BANCO DO BRASIL S.A.',
        'PETR3': 'PETROBRAS (ON)',
        'PETR4': 'PETROBRAS (PN)',
        'VALE3': 'VALE S.A.'
    }
    
    yahoo_symbols = [f'{t.lower()}.sa' for t in tickers.keys()]
    
    print(f"\n🔄 Fetching dividend data from Yahoo Finance...")
    print(f"   Tickers: {list(tickers.keys())}")
    
    # Fetch ALL historical data
    history = Ticker(yahoo_symbols).history(period='max', interval='1d')
    history = history.reset_index()
    
    # Filter for dividend rows only
    div_rows = history[history['dividends'].fillna(0) > 0].copy()
    div_rows['CODIGO'] = div_rows['symbol'].map(normalize_ticker)
    div_rows['date'] = pd.to_datetime(div_rows['date'])
    
    # Get current prices
    price_data = Ticker(yahoo_symbols).price
    current_prices = {}
    for symbol, data in price_data.items():
        if isinstance(data, dict) and data.get('regularMarketPrice'):
            current_prices[normalize_ticker(symbol)] = data['regularMarketPrice']
    
    # TTM calculation
    today = datetime.datetime.today()
    one_year_ago = today - relativedelta(years=1)
    
    print(f"\n✅ Found {len(div_rows)} total dividend payments\n")
    
    # Display each company
    for ticker, company_name in tickers.items():
        company_divs = div_rows[div_rows['CODIGO'] == ticker].copy()
        company_divs = company_divs.sort_values('date')
        
        if company_divs.empty:
            continue
        
        # Calculate stats
        first_date = company_divs['date'].min()
        last_date = company_divs['date'].max()
        total_payments = len(company_divs)
        total_dividends = company_divs['dividends'].sum()
        current_price = current_prices.get(ticker, np.nan)
        
        # TTM dividends
        ttm_divs = company_divs[company_divs['date'] >= one_year_ago]
        ttm_total = ttm_divs['dividends'].sum()
        ttm_yield = (ttm_total / current_price * 100) if current_price else np.nan
        
        print("=" * 90)
        print(f"📌 {ticker} - {company_name}")
        print("=" * 90)
        print(f"   📅 First dividend: {first_date.strftime('%Y-%m-%d')}")
        print(f"   📅 Last dividend:  {last_date.strftime('%Y-%m-%d')}")
        print(f"   📊 Total payments: {total_payments}")
        print(f"   💰 Total dividends: R$ {total_dividends:.2f} per share")
        print(f"   💵 Current price:  R$ {current_price:.2f}" if current_price else "   💵 Current price: N/A")
        print(f"   📈 TTM Dividends:  R$ {ttm_total:.2f} (Yield: {ttm_yield:.2f}%)" if not np.isnan(ttm_yield) else "")
        print()
        
        # Show all dividends
        print(f"   {'Date':<12} {'Dividend (R$)':<15} {'Year':<6}")
        print(f"   {'-'*12} {'-'*15} {'-'*6}")
        
        for _, row in company_divs.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d')
            div_val = row['dividends']
            year = row['date'].year
            print(f"   {date_str:<12} R$ {div_val:<12.4f} {year}")
        
        print()
    
    # Summary table
    print("\n" + "=" * 90)
    print("📊 SUMMARY - CURRENT DIVIDEND YIELDS (TTM)")
    print("=" * 90)
    print(f"\n{'Ticker':<8} {'Company':<30} {'Price':<12} {'TTM Div':<12} {'Yield':<10}")
    print("-" * 80)
    
    for ticker, company_name in tickers.items():
        company_divs = div_rows[div_rows['CODIGO'] == ticker]
        ttm_divs = company_divs[pd.to_datetime(company_divs['date']) >= one_year_ago]
        ttm_total = ttm_divs['dividends'].sum()
        price = current_prices.get(ticker, np.nan)
        dy = (ttm_total / price * 100) if price else np.nan
        
        price_str = f"R$ {price:.2f}" if price else "N/A"
        ttm_str = f"R$ {ttm_total:.2f}"
        dy_str = f"{dy:.2f}%" if not np.isnan(dy) else "N/A"
        
        print(f"{ticker:<8} {company_name[:28]:<30} {price_str:<12} {ttm_str:<12} {dy_str:<10}")
    
    print("\n" + "=" * 90)
    print(f"📅 Data fetched on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)


if __name__ == '__main__':
    main()
