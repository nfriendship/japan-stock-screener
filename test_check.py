import pandas as pd
import yfinance as yf

print("--- 1. yfinanceのテスト開始 ---")
try:
    df_topix = yf.Ticker("^TOPX").history(period="1mo")
    print("TOPIX取得結果:")
    print(df_topix.head())
except Exception as e:
    print("【yfinanceエラー】:", e)

print("\n--- 2. JPX銘柄リスト取得のテスト開始 ---")
url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
try:
    df_jpx = pd.read_excel(url)
    print("JPXリスト取得成功！ 行数:", len(df_jpx))
except Exception as e:
    print("【JPXリスト取得エラー】:", e)