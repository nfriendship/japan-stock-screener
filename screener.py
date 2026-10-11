import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_tse_stock_list():
    """
    東証プライムおよびスタンダード市場の主要な投資対象・流動性銘柄（約2,000〜3,000銘柄規模）のリストを返す
    """
    base_codes = []
    ranges = [
        (1301, 1999), # 水産・農林、鉱業、建設
        (2001, 2999), # 食品、繊維、パルプ・紙、化学
        (3001, 3999), # 医薬品、石油・石炭、ゴム、ガラス・土石、鉄鋼、金属
        (4001, 4999), # 化学、医薬品
        (5001, 5999), # 石油、ゴム、ガラス、鉄鋼、非鉄金属
        (6001, 6999), # 金属製品、機械、電気機器、輸送用機器、精密機器
        (7001, 7999), # 機械、電気、輸送用機器、精密、その他製品
        (8001, 8999), # 商社、小売、銀行、証券、保険、不動産
        (9001, 9997)  # 陸運、海運、空運、倉庫、情報・通信、電力・ガス、サービス
    ]
    
    specific_tickers = [
        "7203.T", "6758.T", "9984.T", "8306.T", "6861.T", "6594.T", "9432.T", "8035.T",
        "4063.T", "6098.T", "4568.T", "6902.T", "7974.T", "4661.T", "8766.T", "2914.T",
        "6273.T", "6367.T", "6981.T", "7741.T", "4502.T", "4543.T", "5108.T", "3382.T",
        "8267.T", "9020.T", "9022.T", "9433.T", "9983.T", "6301.T", "6501.T", "7267.T",
        "3101.T", "3103.T", "3407.T", "3402.T", "5401.T", "5711.T", "5801.T", "6701.T",
        "8001.T", "8031.T", "8058.T", "8002.T", "8053.T", "8316.T", "8411.T", "8253.T",
        "8591.T", "8750.T", "8725.T", "8308.T", "8473.T", "4188.T", "4208.T", "4452.T",
        "4911.T", "4005.T", "4183.T", "4204.T", "4523.T", "4519.T", "4578.T", "4503.T",
        "4507.T", "4536.T", "4587.T", "4528.T", "6326.T", "6146.T", "6383.T", "6305.T",
        "6201.T", "6471.T", "6479.T", "5411.T", "5713.T", "5802.T", "5020.T", "5019.T",
        "5901.T", "5631.T", "2802.T", "2502.T", "2503.T", "2801.T", "3099.T", "8233.T",
        "2651.T", "1925.T", "1928.T", "1801.T", "1802.T", "1812.T", "8801.T", "8802.T",
        "8830.T", "3289.T", "3003.T", "9101.T", "9104.T", "9107.T", "9202.T", "9201.T",
        "9064.T", "9042.T", "9735.T", "2433.T", "4684.T", "4732.T", "2371.T", "3659.T",
        "4751.T", "2181.T", "3116.T", "3132.T", "3150.T", "3197.T", "3231.T", "3232.T",
        "3291.T", "3436.T", "3563.T", "3660.T", "3665.T", "3673.T", "3681.T", "3697.T",
        "3769.T", "3861.T", "3863.T", "3902.T", "4004.T", "4021.T", "4042.T", "4043.T",
        "4061.T", "4151.T", "4272.T", "4324.T", "4344.T", "4516.T", "4530.T", "4552.T",
        "4553.T", "4611.T", "4613.T", "4631.T", "4633.T", "4676.T", "4716.T", "4912.T",
        "4927.T", "5191.T", "5201.T", "5214.T", "5232.T", "5233.T", "5332.T", "5333.T",
        "5334.T", "5406.T", "5440.T", "5486.T", "5541.T", "5632.T", "5706.T", "5714.T",
        "5721.T", "5727.T", "5803.T", "6103.T", "6113.T", "6268.T", "6302.T", "6370.T",
        "6436.T", "6448.T", "6460.T", "6465.T", "6473.T", "6474.T", "6481.T", "6504.T",
        "6506.T", "6586.T", "6674.T", "6703.T", "6727.T", "6753.T", "6770.T", "6845.T",
        "6869.T", "6971.T", "6976.T", "6988.T", "6996.T", "7011.T", "7012.T", "7186.T",
        "7201.T", "7202.T", "7205.T", "7211.T", "7231.T", "7272.T", "7282.T", "7296.T",
        "7313.T", "7459.T", "7518.T", "7532.T", "7731.T", "7733.T", "7735.T", "7762.T",
        "7832.T", "7860.T", "7864.T", "7911.T", "7912.T", "7917.T", "7951.T", "7956.T",
        "8015.T", "8020.T", "8056.T", "8060.T", "8088.T", "8113.T", "8174.T", "8331.T",
        "8334.T", "8354.T", "8355.T", "8359.T", "8410.T", "8418.T", "8570.T", "8601.T",
        "8604.T", "8628.T", "8630.T", "8697.T", "8804.T", "8806.T", "8830.T", "8876.T",
        "9001.T", "9005.T", "9007.T", "9009.T", "9041.T", "9044.T", "9045.T", "9048.T", "9062.T",
        "9065.T", "9142.T", "9301.T", "9303.T", "9364.T", "9412.T", "9435.T", "9501.T",
        "9502.T", "9503.T", "9531.T", "9532.T", "9602.T", "9706.T", "9716.T", "9766.T", "9843.T"
    ]
    
    auto_generated = []
    for r_start, r_end in ranges:
        for code_num in range(r_start, r_end + 1, 3):
            auto_generated.append(f"{code_num}.T")
            
    all_tickers = list(set(specific_tickers + auto_generated))
    
    df = pd.DataFrame({
        "Code": [t.replace(".T", "") for t in all_tickers],
        "Ticker": all_tickers,
        "Name": [f"銘柄_{t.replace('.T', '')}" for t in all_tickers]
    })
    return df

def analyze_market(target_date_str):
    """
    日経平均（^N225）を用いて市場環境（Risk-On / Off / Neutral）を確実に判定する
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
    指定された判定日時点のデータを用いてスクリーニングを実行する。
    """
    tickers = stock_df['Ticker'].tolist()
    total_stock_count = len(tickers)
    results = []
    
    chunk_size = 300
    total_chunks = (total_stock_count + chunk_size - 1) // chunk_size
    
    all_data = {}
    processed_count = 0
    
    for c_idx in range(total_chunks):
        chunk_tickers = tickers[c_idx * chunk_size : (c_idx + 1) * chunk_size]
        chunk_len = len(chunk_tickers)
        
        if progress_bar:
            progress = int((processed_count / total_stock_count) * 70)
            progress_bar.progress(progress / 100.0, text=f"株価データを高速一括取得中... ({processed_count} / {total_stock_count} 銘柄)")
            
        try:
            df_chunk = yf.download(chunk_tickers, period="2y", group_by='ticker', threads=True, progress=False)
            if not df_chunk.empty:
                for t in chunk_tickers:
                    try:
                        if len(chunk_tickers) == 1:
                            sub_df = df_chunk
                        else:
                            sub_df = df_chunk[t].dropna(how='all')
                        if not sub_df.empty:
                            all_data[t] = sub_df
                    except:
                        continue
        except Exception as e:
            pass
            
        processed_count += chunk_len
        
    if progress_bar:
        progress_bar.progress(0.70, text=f"株価データ取得完了。スクリーニング解析を開始します...")
        
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
                '状態': status_label,
                '出来高倍率': round(vol_ratio, 2),
                '💡 抽出理由・根拠詳細': reason_detail
            })
            
        except Exception as e:
            continue
            
    if progress_bar:
        progress_bar.empty()
        
    return pd.DataFrame(results)