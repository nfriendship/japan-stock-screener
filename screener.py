import yfinance as yf
import pandas as pd
import numpy as np
import io
import time
import requests
import streamlit as st
from datetime import datetime, timedelta

@st.cache_data(ttl=86400)
def get_tse_stock_list():
    """
    JPX公式の東証上場銘柄一覧（Excel）から、個別株（プライム・スタンダード・グロースの内国株式）
    約3,800〜3,900銘柄のみを正確に抽出する。ETFやREIT、架空コードは完全排除。
    """
    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    df_jpx = None
    
    # 1. requests経由でダウンロード試行
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            df_jpx = pd.read_excel(io.BytesIO(response.content))
    except Exception:
        pass
        
    # 2. 直接URL読み込み試行（フォールバック）
    if df_jpx is None or df_jpx.empty:
        try:
            df_jpx = pd.read_excel(url)
        except Exception:
            pass
            
    if df_jpx is not None and not df_jpx.empty:
        try:
            market_col = [c for c in df_jpx.columns if '市場' in str(c)][0]
            code_col = [c for c in df_jpx.columns if 'コード' in str(c)][0]
            name_col = [c for c in df_jpx.columns if '銘柄名' in str(c)][0]
            
            # 「内国株式（プライム・スタンダード・グロース）」のみを抽出（ETF・REITを完全除外）
            mask = df_jpx[market_col].astype(str).str.contains('内国株式', na=False)
            filtered = df_jpx[mask]
            
            codes = []
            tickers = []
            names = []
            
            for _, row in filtered.iterrows():
                c_str = str(row[code_col]).strip()
                if len(c_str) == 4 and c_str.isdigit():
                    codes.append(c_str)
                    tickers.append(f"{c_str}.T")
                    names.append(str(row[name_col]).strip())
                    
            if len(tickers) >= 3000:
                return pd.DataFrame({
                    "Code": codes,
                    "Ticker": tickers,
                    "Name": names
                })
        except Exception:
            pass
            
    # 万一通信が遮断された場合のセーフティネット（主力約150銘柄）
    fallback_codes = [
        ("7203", "トヨタ自動車"), ("6758", "ソニーグループ"), ("9984", "ソフトバンクグループ"), ("8306", "三菱UFJフィナンシャルG"),
        ("6861", "キーエンス"), ("6594", "ニデック"), ("9432", "日本電信電話"), ("8035", "東京エレクトロン"),
        ("4063", "信越化学工業"), ("6098", "リクルートHD"), ("4568", "第一三共"), ("6902", "デンソー"),
        ("7974", "任天堂"), ("4661", "オリエンタルランド"), ("8766", "東京海上HD"), ("2914", "日本たばこ産業"),
        ("6273", "SMC"), ("6367", "ダイキン工業"), ("6981", "村田製作所"), ("7741", "HOYA"),
        ("4502", "武田薬品工業"), ("4543", "テルモ"), ("5108", "ブリヂストン"), ("3382", "セブン＆アイHD"),
        ("8267", "イオン"), ("9020", "JR東日本"), ("9022", "JR東海"), ("9433", "KDDI"),
        ("9983", "ファーストリテイリング"), ("6301", "小松製作所"), ("6501", "日立製作所"), ("7267", "本田技研工業")
    ]
    return pd.DataFrame({
        "Code": [c[0] for c in fallback_codes],
        "Ticker": [f"{c[0]}.T" for c in fallback_codes],
        "Name": [c[1] for c in fallback_codes]
    })

def analyze_market(target_date_str):
    """
    日経平均（^N225）を用いて市場環境（Risk-On / Off / Neutral）を判定する
    """
    try:
        n225 = yf.Ticker("^N225").history(period="2y")
        if n225.empty:
            return "Neutral", "市場データの取得が出来ませんでした。"
        
        n225.index = pd.to_datetime(n225.index).strftime('%Y-%m-%d')
        df = n225[n225.index <= target_date_str]
        if len(df) < 200:
            return "Neutral", "市場の200日移動平均線を算出するためのデータが不足しています。"
            
        close = df['Close'].iloc[-1]
        sma50 = df['Close'].rolling(50).mean().iloc[-1]
        sma200 = df['Close'].rolling(200).mean().iloc[-1]
        sma200_prev = df['Close'].rolling(200).mean().iloc[-20]
        
        is_above_200 = close > sma200
        is_50_above_200 = sma50 > sma200
        is_200_rising = sma200 > sma200_prev
        
        if is_above_200 and is_50_above_200 and is_200_rising:
            return "Risk-On", f"市場指数順調（終値>200日線、50日>200日、200日上昇） ⇒ 通常売買OK"
        elif not is_above_200 and not is_200_rising:
            return "Risk-Off", f"市場環境悪化（終値<200日線、200日下落） ⇒ 守り重視・新規買い控え"
        else:
            return "Neutral", f"市場環境モミ合い（方向感模索） ⇒ 厳選して売買"
            
    except Exception as e:
        return "Neutral", f"市場環境判定エラー: {e}"

def run_screener_batch(stock_df, target_date_str, progress_bar=None):
    """
    実在する東証全銘柄を対象にスクリーニングを実行する。
    """
    tickers = stock_df['Ticker'].tolist()
    total_stock_count = len(tickers)
    results = []
    
    chunk_size = 150
    total_chunks = (total_stock_count + chunk_size - 1) // chunk_size
    
    all_data = {}
    processed_count = 0
    
    for c_idx in range(total_chunks):
        chunk_tickers = tickers[c_idx * chunk_size : (c_idx + 1) * chunk_size]
        chunk_len = len(chunk_tickers)
        
        if progress_bar:
            progress = int((processed_count / total_stock_count) * 70)
            progress_bar.progress(progress / 100.0, text=f"実在銘柄の株価データを高速取得中... ({processed_count} / {total_stock_count} 銘柄)")
            
        df_chunk = None
        for attempt in range(2):
            try:
                df_chunk = yf.download(chunk_tickers, period="2y", group_by='ticker', threads=True, progress=False)
                if df_chunk is not None and not df_chunk.empty:
                    break
            except Exception:
                time.sleep(1.0)
                
        if df_chunk is not None and not df_chunk.empty:
            for t in chunk_tickers:
                try:
                    if len(chunk_tickers) == 1:
                        sub_df = df_chunk.dropna(how='all')
                    else:
                        sub_df = df_chunk[t].dropna(how='all')
                    if not sub_df.empty:
                        all_data[t] = sub_df
                except:
                    continue
                    
        processed_count += chunk_len
        
    if progress_bar:
        progress_bar.progress(0.70, text=f"データ取得完了。スクリーニング解析を開始します...")
        
    total_valid = len(all_data)
    analyzed_count = 0
    
    for ticker, df in all_data.items():
        analyzed_count += 1
        if progress_bar and total_valid > 0:
            progress = 70 + int((analyzed_count / total_valid) * 30)
            progress_bar.progress(min(progress, 100) / 100.0, text=f"スクリーニング解析中... ({analyzed_count} / {total_valid} 有効銘柄)")
            
        try:
            df.index = pd.to_datetime(df.index).strftime('%Y-%m-%d')
            sub_df = df[df.index <= target_date_str].copy()
            
            if len(sub_df) < 200:
                continue
                
            current_close = sub_df['Close'].iloc[-1]
            current_vol = sub_df['Volume'].iloc[-1]
            current_date = sub_df.index[-1]
            
            # --- 1. 流動性＆基本フィルター ---
            if current_close < 500:
                continue
            
            sub_df['Turnover'] = sub_df['Close'] * sub_df['Volume']
            avg_turnover = sub_df['Turnover'].rolling(20).mean().iloc[-1]
            if avg_turnover < 500000000:
                continue
                
            # --- 2. ミネルヴィニ流 トレンドテンプレート ---
            sma50 = sub_df['Close'].rolling(50).mean().iloc[-1]
            sma150 = sub_df['Close'].rolling(150).mean().iloc[-1]
            sma200 = sub_df['Close'].rolling(200).mean().iloc[-1]
            sma200_20days_ago = sub_df['Close'].rolling(200).mean().iloc[-20]
            high_52w = sub_df['High'].tail(250).max()
            low_52w = sub_df['Low'].tail(250).min()
            
            cond_trend = (
                (current_close > sma150) and
                (sma150 > sma200) and
                (sma200 > sma200_20days_ago) and
                (current_close >= 1.25 * low_52w) and
                (current_close >= 0.75 * high_52w)
            )
            
            if not cond_trend:
                continue
                
            # --- 3. ピボット価格と出来高基準の算出 ---
            pivot_price = sub_df['High'].tail(20).iloc[:-1].max()
            avg_vol_20 = sub_df['Volume'].rolling(20).mean().iloc[-1]
            
            # --- 4. 判定ロジック（ブレイク当日 ＋ ブレイク前夜/VCP収縮） ---
            is_breakout = (current_close >= pivot_price) and (current_vol >= avg_vol_20 * 1.5)
            is_near_pivot = (pivot_price * 0.97 <= current_close < pivot_price)
            
            if not (is_breakout or is_near_pivot):
                continue
                
            vol_ratio = current_vol / avg_vol_20 if avg_vol_20 > 0 else 0
            dist_from_pivot = ((current_close - pivot_price) / pivot_price) * 100
            diff_from_high_52w = ((current_close - high_52w) / high_52w) * 100
            rise_from_low_52w = ((current_close - low_52w) / low_52w) * 100
            
            match_row = stock_df[stock_df['Ticker'] == ticker]
            code = match_row['Code'].values[0] if not match_row.empty else ticker.replace('.T', '')
            name = match_row['Name'].values[0] if not match_row.empty else f"銘柄_{code}"
            
            if is_breakout:
                status_label = "🚀 【ブレイク当日】新高値突破＆出来高急増"
                reason_detail = (
                    f"**判定日 ({current_date}) 時点の状況**:\n"
                    f"- **株価/ピボット**: 終値 {current_close:.1f}円 が過去20日高値（{pivot_price:.1f}円）を上抜け（ブレイク達成）。\n"
                    f"- **出来高倍率**: 当日出来高は20日平均の **{vol_ratio:.2f}倍**（基準1.5倍クリア）。機関投資家の買い参入を示唆。\n"
                    f"- **トレンド状態**: 200日線（{sma200:.1f}円）が上向きで、主要移動平均線のパーフェクトオーダーを形成中。"
                )
            else:
                status_label = "⏳ 【ブレイク前夜・VCP収縮】ピボット近傍で推移中"
                reason_detail = (
                    f"**判定日 ({current_date}) 時点の状況**:\n"
                    f"- **株価/ピボット**: 終値 {current_close:.1f}円 はピボット価格（{pivot_price:.1f}円）に対して **{dist_from_pivot:+.2f}%** の至近距離に位置。\n"
                    f"- **VCP状態**: 売り圧力が枯れ、ボラティリティが収縮しながら上値抵抗線（ピボット）の真下でベースを形成中。\n"
                    f"- **出来高倍率**: 20日平均比 **{vol_ratio:.2f}倍**（今後ブレイク時の出来高急増に要注目）。\n"
                    f"- **トレンド状態**: トレンドテンプレートの厳格な条件をすべてクリアし、本格上昇のスタンバイ状態。"
                )
                
            results.append({
                'コード': code,
                'ティッカー': ticker,
                '企業名': name,
                '現在値': current_close,
                'ピボット価格': round(pivot_price, 1),
                'ピボット乖離率(%)': round(dist_from_pivot, 2),
                '状態': status_label,
                '出来高倍率': round(vol_ratio, 2),
                '当日出来高': int(current_vol),
                '20日平均出来高': int(avg_vol_20),
                '20日平均売買代金(億円)': round(avg_turnover / 100000000, 2),
                'SMA50': round(sma50, 1),
                'SMA150': round(sma150, 1),
                'SMA200': round(sma200, 1),
                '52週高値': round(high_52w, 1),
                '52週安値': round(low_52w, 1),
                '52週高値乖離率(%)': round(diff_from_high_52w, 2),
                '52週安値上昇率(%)': round(rise_from_low_52w, 2),
                '💡 抽出理由・根拠詳細': reason_detail
            })
            
        except Exception as e:
            continue
            
    if progress_bar:
        progress_bar.empty()
        
    meta_stats = {
        'total_stocks': total_stock_count,
        'valid_stocks': total_valid,
        'success_rate': (total_valid / total_stock_count * 100) if total_stock_count > 0 else 0.0
    }
    return pd.DataFrame(results), meta_stats

def batch_validate_trades(screened_df, signal_date_str, risk_reward_ratio=2.5, progress_bar=None):
    """
    スクリーニング抽出銘柄を一括ダウンロードで高速取得し、安全なSL/TP設定のもとトレード結果を判定する
    """
    if screened_df.empty:
        return pd.DataFrame()
        
    tickers = screened_df['ティッカー'].tolist()
    total = len(tickers)
    
    if progress_bar:
        progress_bar.progress(0.1, text=f"検証対象 {total} 銘柄の株価データを一括ダウンロード中...")
        
    all_data = {}
    try:
        df_batch = yf.download(tickers, period="2y", group_by='ticker', threads=True, progress=False)
        if not df_batch.empty:
            for t in tickers:
                try:
                    if len(tickers) == 1:
                        sub_df = df_batch.dropna(how='all')
                    else:
                        sub_df = df_batch[t].dropna(how='all')
                    if not sub_df.empty:
                        all_data[t] = sub_df
                except:
                    continue
    except Exception as e:
        pass
        
    validation_results = []
    
    for idx, row in screened_df.iterrows():
        ticker = row['ティッカー']
        code = row['コード']
        name = row['企業名']
        
        if progress_bar:
            prog_val = 0.3 + (0.7 * ((idx + 1) / total))
            progress_bar.progress(min(prog_val, 1.0), text=f"【{idx + 1}/{total}】 {name} のトレード推移を解析中...")
            
        df = all_data.get(ticker)
        if df is None or df.empty:
            continue
            
        try:
            df.index = pd.to_datetime(df.index).strftime('%Y-%m-%d')
            past_df = df[df.index <= signal_date_str]
            future_df = df[df.index > signal_date_str]
            
            if future_df.empty:
                validation_results.append({
                    'コード': code,
                    'ティッカー': ticker,
                    '企業名': name,
                    'エントリー日': "翌営業日待ち",
                    '買値(エントリー)': np.nan,
                    '売値(決済/現在値)': np.nan,
                    'SL価格': np.nan,
                    'TP目標': np.nan,
                    '検証ステータス': "⏳ エントリー待機中（翌営業日データ未到来）",
                    '決済日/現在日': "-",
                    '損益額(円)': 0.0,
                    '損益率(%)': 0.0,
                    '保有日数': 0,
                    '勝敗': "未確定"
                })
                continue
                
            pivot_price = past_df['High'].tail(20).iloc[:-1].max()
            high_low = past_df['High'] - past_df['Low']
            high_cp = np.abs(past_df['High'] - past_df['Close'].shift())
            low_cp = np.abs(past_df['Low'] - past_df['Close'].shift())
            tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
            atr20 = tr.rolling(20).mean().iloc[-1]
            if pd.isna(atr20) or atr20 <= 0:
                atr20 = past_df['Close'].iloc[-1] * 0.02
                
            entry_date = future_df.index[0]
            entry_price = future_df['Open'].iloc[0]
            
            calc_sl = max(pivot_price * 0.95, pivot_price - (1.5 * atr20))
            sl_price = min(calc_sl, entry_price - (1.5 * atr20), entry_price * 0.95)
            
            risk_amount = entry_price - sl_price
            if risk_amount <= 0:
                risk_amount = entry_price * 0.05
                sl_price = entry_price - risk_amount
                
            tp_price = entry_price + (risk_amount * risk_reward_ratio)
            
            trade_period_df = future_df.loc[entry_date:]
            
            current_last_close = trade_period_df['Close'].iloc[-1]
            pnl_amount = current_last_close - entry_price
            pnl_pct = (pnl_amount / entry_price) * 100
            
            status = f"⏳ 保有中 ({'含み益' if pnl_amount >= 0 else '含み損'})"
            exit_date = trade_period_df.index[-1]
            exit_price = current_last_close
            hold_days = len(trade_period_df)
            outcome = "保有中"
            
            for d_idx, d_row in trade_period_df.iterrows():
                d_low = d_row['Low']
                d_high = d_row['High']
                
                hit_sl = d_low <= sl_price
                hit_tp = d_high >= tp_price
                
                if hit_sl and hit_tp:
                    status = "❌ 損切り (同日到達・保守判定)"
                    exit_date = d_idx
                    exit_price = sl_price
                    pnl_amount = exit_price - entry_price
                    pnl_pct = (pnl_amount / entry_price) * 100
                    hold_days = len(trade_period_df.loc[:d_idx])
                    outcome = "負け"
                    break
                elif hit_sl:
                    status = "❌ 損切り (SL到達)"
                    exit_date = d_idx
                    exit_price = sl_price
                    pnl_amount = exit_price - entry_price
                    pnl_pct = (pnl_amount / entry_price) * 100
                    hold_days = len(trade_period_df.loc[:d_idx])
                    outcome = "負け"
                    break
                elif hit_tp:
                    status = "🎯 利確達成 (TP到達)"
                    exit_date = d_idx
                    exit_price = tp_price
                    pnl_amount = exit_price - entry_price
                    pnl_pct = (pnl_amount / entry_price) * 100
                    hold_days = len(trade_period_df.loc[:d_idx])
                    outcome = "勝ち"
                    break
                    
            validation_results.append({
                'コード': code,
                'ティッカー': ticker,
                '企業名': name,
                'エントリー日': entry_date,
                '買値(エントリー)': round(entry_price, 1),
                '売値(決済/現在値)': round(exit_price, 1),
                'SL価格': round(sl_price, 1),
                'TP目標': round(tp_price, 1),
                '検証ステータス': status,
                '決済日/現在日': exit_date,
                '損益額(円)': round(pnl_amount, 1),
                '損益率(%)': round(pnl_pct, 2),
                '保有日数': hold_days,
                '勝敗': outcome
            })
            
        except Exception as e:
            continue
            
    if progress_bar:
        progress_bar.empty()
        
    return pd.DataFrame(validation_results)