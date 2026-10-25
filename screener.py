import yfinance as yf
import pandas as pd
import numpy as np
import time
import os
import pickle
from datetime import datetime, timedelta

CACHE_DIR = "cache_data"
STOCK_CACHE_FILE = os.path.join(CACHE_DIR, "stock_history_cache.pkl")
MARKET_CACHE_FILE = os.path.join(CACHE_DIR, "market_history_cache.pkl")

def ensure_cache_dir():
    """キャッシュフォルダを作成"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def load_local_cache(cache_file):
    """キャッシュを安全に読み込む"""
    ensure_cache_dir()
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except Exception:
            return {}
    return {}

def save_local_cache(cache_file, data_dict):
    """キャッシュを安全に保存する"""
    ensure_cache_dir()
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(data_dict, f)
    except Exception:
        pass

def clear_all_cache():
    """キャッシュ全消去"""
    if os.path.exists(STOCK_CACHE_FILE):
        try:
            os.remove(STOCK_CACHE_FILE)
        except:
            pass
    if os.path.exists(MARKET_CACHE_FILE):
        try:
            os.remove(MARKET_CACHE_FILE)
        except:
            pass

def merge_stock_df(old_df, new_df):
    """新旧の株価データを日付インデックスで安全に結合・重複排除する"""
    if old_df is None or old_df.empty:
        return new_df
    if new_df is None or new_df.empty:
        return old_df
    combined = pd.concat([old_df, new_df])
    combined = combined[~combined.index.duplicated(keep='last')]
    combined.sort_index(inplace=True)
    return combined

def get_tse_stock_list():
    """東証個別銘柄リスト生成（ETF・REITは事前除外）"""
    major_companies = {
        "7203": "トヨタ自動車", "6758": "ソニーグループ", "9984": "ソフトバンクグループ", "8306": "三菱UFJフィナンシャルG",
        "6861": "キーエンス", "6594": "ニデック", "9432": "日本電信電話", "8035": "東京エレクトロン",
        "4063": "信越化学工業", "6098": "リクルートホールディングス", "4568": "第一三共", "6902": "デンソー",
        "7974": "任天堂", "4661": "オリエンタルランド", "8766": "東京海上ホールディングス", "2914": "日本たばこ産業",
        "6273": "SMC", "6367": "ダイキン工業", "6981": "村田製作所", "7741": "HOYA",
        "4502": "武田薬品工業", "4543": "テルモ", "5108": "ブリヂストン", "3382": "セブン＆アイ・ホールディングス",
        "8267": "イオン", "9020": "東日本旅客鉄道", "9022": "東海旅客鉄道", "9433": "KDDI",
        "9983": "ファーストリテイリング", "6301": "小松製作所", "6501": "日立製作所", "7267": "本田技研工業",
        "3101": "東洋紡", "3103": "ユニチカ", "3407": "旭化成", "3402": "東レ",
        "5401": "日本製鉄", "5711": "三菱マテリアル", "5801": "古河電気工業", "6701": "日本電気",
        "8001": "伊藤忠商事", "8031": "三井物産", "8058": "三菱商事", "8002": "丸紅",
        "8053": "住友商事", "8316": "三井武友フィナンシャルG", "8411": "みずほフィナンシャルG", "8253": "クレディセゾン",
        "8591": "オリックス", "8750": "第一生命ホールディングス", "8725": "MS&ADインシュアランスG", "8308": "りそなホールディングス",
        "8473": "SBIホールディングス", "4188": "三菱ケミカルグループ", "4208": "UBE", "4452": "花王",
        "4911": "資生堂", "4005": "住友化学", "4183": "三井化学", "4204": "積水化学工業",
        "4523": "エーザイ", "4519": "中外製薬", "4578": "大塚ホールディングス", "4503": "アステラス製薬",
        "4507": "塩野義製薬", "4536": "参天製薬", "4587": "ペプチドリーム", "4528": "小野薬品工業",
        "6326": "クボタ", "6146": "ディスコ", "6383": "ダイフク", "6305": "日立建機",
        "6201": "豊田自動織機", "6471": "日本精工", "6479": "ミネベアミツミ", "5411": "JFEホールディングス",
        "5713": "住友金属鉱山", "5802": "住友電気工業", "5020": "ENEOSホールディングス", "5019": "出光興産",
        "5901": "東洋製罐グループHD", "5631": "日本製鋼所", "2802": "味の素", "2502": "アサヒグループHD",
        "2503": "キリンホールディングス", "2801": "キッコーマン", "3099": "三越伊勢丹HD", "8233": "高島屋",
        "2651": "ローソン", "1925": "大和ハウス工業", "1928": "積水ハウス", "1801": "大成建設",
        "1802": "大林組", "1812": "鹿島建設", "8801": "三井不動産", "8802": "三菱地所",
        "8830": "住友不動産", "3289": "東急不動産HD", "3003": "ヒューリック", "9101": "日本郵船",
        "9104": "商船三井", "9107": "川崎汽船", "9202": "ANAホールディングス", "9201": "日本航空",
        "9064": "ヤマトホールディングス", "9042": "阪急阪神HD", "9735": "セコム", "2433": "博報堂DY HD",
        "4684": "オービック", "4732": "ユー・エス・エス", "2371": "カカクコム", "3659": "ネクソン",
        "4751": "サイバーエージェント", "2181": "パーソルHD", "3116": "トヨタ紡織", "3132": "マクニカHD",
        "3150": "グリムス", "3197": "すかいらーくHD", "3231": "野村不動産HD", "3291": "飯田グループHD",
        "3436": "SUMCO", "3563": "FOOD & LIFE COMPANIES", "3660": "アイスタイル", "3697": "SHIFT",
        "3769": "GMOペイメントゲートウェイ", "3861": "王子ホールディングス", "3863": "日本製紙", "4004": "レゾナックHD",
        "4021": "日産化学", "4042": "東ソー", "4043": "トクヤマ", "4061": "デンカ",
        "4151": "協和キリン", "4272": "日本化薬", "4324": "電通グループ", "4344": "ソースネクスト",
        "5191": "住友理工", "5201": "AGC", "5214": "日本電気硝子", "5232": "住友大阪セメント",
        "5332": "TOTO", "5333": "日本ガイシ", "5334": "日本特殊陶業", "5406": "神戸製鋼所",
        "5541": "大平洋金属", "5706": "三井金属鉱業", "5714": "DOWA HD", "5803": "フジクラ",
        "6103": "オークマ", "6113": "アマダ", "6268": "ナブテスコ", "6370": "栗田工業",
        "6436": "アマノ", "6448": "ブラザー工業", "6460": "セガサミーHD", "6481": "THK",
        "6504": "富士電機", "6506": "安川電機", "6586": "マキタ", "6674": "GSユアサ",
        "6703": "沖電気工業", "6727": "ワコム", "6753": "シャープ", "6770": "アルプスアルパイン",
        "6845": "アズビル", "6869": "シスメックス", "6971": "京セラ", "6976": "太陽誘電",
        "7011": "三菱重工業", "7012": "川崎重工業", "7186": "コンコルディアFG", "7201": "日産自動車",
        "7202": "いすゞ自動車", "7205": "日野自動車", "7211": "三菱自動車工業", "7272": "ヤマハ発動機",
        "7731": "ニコン", "7733": "オリンパス", "7735": "SCREEN HD", "7832": "バンダイナムコHD",
        "7911": "TOPPAN HD", "7912": "大日本印刷", "7951": "ヤマハ", "8056": "BIPROGY",
        "8088": "岩谷産業", "8113": "ユニ・チャーム", "8601": "大和証券グループ本社", "8604": "野村ホールディングス",
        "8697": "日本取引所グループ", "9001": "東武鉄道", "9005": "東急", "9007": "小田急電鉄",
        "9041": "近鉄グループHD", "9142": "九州旅客鉄道", "9501": "東京電力HD", "9502": "中部電力",
        "9503": "関西電力", "9531": "東京瓦斯", "9532": "大阪瓦斯", "9602": "東宝",
        "9706": "日本空港ビルデング", "9716": "乃村工藝社", "9766": "コナミグループ", "9843": "ニトリHD"
    }

    individual_1000s = [
        "1301", "1332", "1333", "1375", "1376", "1377", "1379", "1407", "1414", "1417",
        "1419", "1429", "1430", "1433", "1435", "1447", "1448", "1514", "1515", "1518",
        "1605", "1662", "1663"
    ]
    
    ranges = [
        (1712, 1999), (2001, 2999), (3001, 3999), (4001, 4999),
        (5001, 5999), (6001, 6999), (7001, 7999), (8001, 8999), (9001, 9997)
    ]
    
    all_codes = set(major_companies.keys()).union(set(individual_1000s))
    for r_start, r_end in ranges:
        for code_num in range(r_start, r_end + 1, 3):
            all_codes.add(str(code_num))
            
    sorted_codes = sorted(list(all_codes))
    tickers = [f"{c}.T" for c in sorted_codes]
    names = [major_companies.get(c, f"東証_{c}") for c in sorted_codes]
    
    return pd.DataFrame({
        "Code": sorted_codes,
        "Ticker": tickers,
        "Name": names
    })

def analyze_market(target_date_str, use_cache=True):
    """日経平均の市場判定"""
    target_dt = pd.to_datetime(target_date_str)
    needed_start_dt = target_dt - timedelta(days=450)
    needed_start_str = needed_start_dt.strftime('%Y-%m-%d')
    
    df_n225 = None
    market_cache = load_local_cache(MARKET_CACHE_FILE) if use_cache else {}
    
    if use_cache and "^N225" in market_cache:
        temp_df = market_cache["^N225"]
        first_d = pd.to_datetime(temp_df.index[0]).strftime('%Y-%m-%d')
        last_d = pd.to_datetime(temp_df.index[-1]).strftime('%Y-%m-%d')
        if first_d <= needed_start_str and last_d >= target_date_str:
            df_n225 = temp_df
            
    if df_n225 is None:
        try:
            n225_ticker = yf.Ticker("^N225")
            new_n225 = n225_ticker.history(start=needed_start_str)
            if new_n225 is not None and not new_n225.empty:
                df_n225 = merge_stock_df(market_cache.get("^N225"), new_n225)
                market_cache["^N225"] = df_n225
                save_local_cache(MARKET_CACHE_FILE, market_cache)
        except Exception:
            if "^N225" in market_cache:
                df_n225 = market_cache["^N225"]
                
    if df_n225 is None or df_n225.empty:
        return "Neutral", "市場環境判定待機中（キャッシュまたは再試行推奨）"
        
    try:
        df = df_n225.copy()
        df.index = pd.to_datetime(df.index).strftime('%Y-%m-%d')
        sub_df = df[df.index <= target_date_str]
        if len(sub_df) < 200:
            return "Neutral", "市場の200日移動平均線を算出するためのデータが不足しています。"
            
        close = sub_df['Close'].iloc[-1]
        sma50 = sub_df['Close'].rolling(50).mean().iloc[-1]
        sma200 = sub_df['Close'].rolling(200).mean().iloc[-1]
        sma200_prev = sub_df['Close'].rolling(200).mean().iloc[-20]
        
        is_above_200 = close > sma200
        is_50_above_200 = sma50 > sma200
        is_200_rising = sma200 > sma200_prev
        
        if is_above_200 and is_50_above_200 and is_200_rising:
            return "Risk-On", f"市場指数順調（終値>200日線、50日>200日、200日上昇） ⇒ 通常売買OK"
        elif not is_above_200 and not is_200_rising:
            return "Risk-Off", f"市場環境悪化（終値<200日線、200日下落） ⇒ 守り重視・本命買い見送り推奨"
        else:
            return "Neutral", f"市場環境モミ合い（方向感模索） ⇒ 厳選して売買（ダマシ警戒）"
    except Exception as e:
        return "Neutral", f"市場環境判定エラー: {e}"

def run_screener_batch(stock_df, target_date_str, use_cache=True, progress_bar=None):
    """
    【修正完全版】レイトステージ最上位完全排除 ＆ チェイス禁止 ＆ 地合い連動
    """
    tickers = stock_df['Ticker'].tolist()
    total_stock_count = len(tickers)
    results = []
    
    market_status, _ = analyze_market(target_date_str, use_cache=use_cache)
    
    target_dt = pd.to_datetime(target_date_str)
    needed_start_dt = target_dt - timedelta(days=450)
    needed_start_str = needed_start_dt.strftime('%Y-%m-%d')
    
    all_data = load_local_cache(STOCK_CACHE_FILE)
    cached_count_before = len(all_data)
    
    missing_tickers = []
    if not use_cache:
        missing_tickers = tickers
    else:
        for t in tickers:
            if t not in all_data:
                missing_tickers.append(t)
            else:
                t_df = all_data[t]
                t_first_date = pd.to_datetime(t_df.index[0]).strftime('%Y-%m-%d')
                t_last_date = pd.to_datetime(t_df.index[-1]).strftime('%Y-%m-%d')
                if t_first_date > needed_start_str or t_last_date < target_date_str:
                    missing_tickers.append(t)
                    
    if missing_tickers:
        chunk_size = 150
        total_chunks = (len(missing_tickers) + chunk_size - 1) // chunk_size
        processed_count = 0
        
        for c_idx in range(total_chunks):
            chunk_tickers = missing_tickers[c_idx * chunk_size : (c_idx + 1) * chunk_size]
            chunk_len = len(chunk_tickers)
            
            if progress_bar:
                progress = int((processed_count / len(missing_tickers)) * 60)
                progress_bar.progress(progress / 100.0, text=f"必要な株価データを取得・更新中... ({processed_count} / {len(missing_tickers)} 銘柄)")
                
            df_chunk = None
            for attempt in range(2):
                try:
                    df_chunk = yf.download(chunk_tickers, start=needed_start_str, group_by='ticker', threads=True, progress=False)
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
                            all_data[t] = merge_stock_df(all_data.get(t), sub_df)
                    except:
                        continue
                        
            processed_count += chunk_len
            
        save_local_cache(STOCK_CACHE_FILE, all_data)
        
    if progress_bar:
        progress_bar.progress(0.70, text=f"データ準備完了。スクリーニング解析を実行中...")
        
    total_valid = len(all_data)
    analyzed_count = 0
    
    for ticker, df in all_data.items():
        analyzed_count += 1
        if progress_bar and total_valid > 0:
            progress = 70 + int((analyzed_count / total_valid) * 30)
            progress_bar.progress(min(progress, 100) / 100.0, text=f"スクリーニング解析中... ({analyzed_count} / {total_valid} 有効銘柄)")
            
        try:
            match_row = stock_df[stock_df['Ticker'] == ticker]
            code = match_row['Code'].values[0] if not match_row.empty else ticker.replace('.T', '')
            name = match_row['Name'].values[0] if not match_row.empty else f"東証_{code}"
            
            # --- 0. ETF・REIT等のノイズ除外 ---
            if any(kw in name for kw in ['ETF', '上場投信', '投資法人', 'REIT', '投信']):
                continue
                
            df.index = pd.to_datetime(df.index).strftime('%Y-%m-%d')
            sub_df = df[df.index <= target_date_str].copy()
            
            if len(sub_df) < 200:
                continue
                
            current_close = sub_df['Close'].iloc[-1]
            current_vol = sub_df['Volume'].iloc[-1]
            current_date = sub_df.index[-1]
            
            if current_close < 500:
                continue
            
            sub_df['Turnover'] = sub_df['Close'] * sub_df['Volume']
            avg_turnover = sub_df['Turnover'].rolling(20).mean().iloc[-1]
            turnover_oku = avg_turnover / 100000000.0
            
            if turnover_oku < 5.0:
                continue
                
            sma50 = sub_df['Close'].rolling(50).mean().iloc[-1]
            sma150 = sub_df['Close'].rolling(150).mean().iloc[-1]
            sma200 = sub_df['Close'].rolling(200).mean().iloc[-1]
            sma200_20days_ago = sub_df['Close'].rolling(200).mean().iloc[-20]
            high_52w = sub_df['High'].tail(250).max()
            low_52w = sub_df['Low'].tail(250).min()
            
            cond_trend_base = (
                (current_close > sma150) and
                (sma150 > sma200) and
                (sma200 > sma200_20days_ago) and
                (current_close >= 1.25 * low_52w) and
                (current_close >= 0.75 * high_52w)
            )
            if not cond_trend_base:
                continue
                
            rise_from_low_52w = ((current_close - low_52w) / low_52w) * 100
            sma200_bias = ((current_close - sma200) / sma200) * 100
            
            # ==============================================================
            # 🛑 【第1の絶対防壁】レイトステージ（過熱バブル）の物理的完全排除
            # 安値から150%超の上昇、または200日線から25%超の上方乖離は一行で即座に除外
            # （※5801や7826等のバブル銘柄はブレイク当日・前夜問わず一切通過不可）
            # ==============================================================
            if rise_from_low_52w > 150.0 or sma200_bias > 25.0:
                continue
                
            pivot_price = sub_df['High'].tail(20).iloc[:-1].max()
            avg_vol_20 = sub_df['Volume'].rolling(20).mean().iloc[-1]
            vol_ratio = (current_vol / avg_vol_20) if avg_vol_20 > 0 else 0
            dist_from_pivot = ((current_close - pivot_price) / pivot_price) * 100
            diff_from_high_52w = ((current_close - high_52w) / high_52w) * 100
            
            # 🛑 【チェイス禁止ルール】
            raw_breakout = (current_close >= pivot_price) and (vol_ratio >= 1.5) and (dist_from_pivot <= 5.0)
            raw_near_pivot = (-2.5 <= dist_from_pivot < 0.0)
            
            if not (raw_breakout or raw_near_pivot):
                continue
                
            rank = None
            status_label = None
            reason_detail = None
            
            # ----------------------------------------------------------
            # 🏆 【本命・高勝率S級】判定条件
            # ※市場環境が Risk-On の時のみ許可（Risk-OffやNeutralでは本命買いは見送り！）
            # ----------------------------------------------------------
            is_main_tier = False
            if market_status == "Risk-On" and turnover_oku >= 20.0 and diff_from_high_52w >= -5.0:
                # パターンA：ブレイク当日（初動ゾーン+2.5%以内限定）
                if raw_breakout and (1.5 <= vol_ratio <= 3.0) and (0.0 <= dist_from_pivot <= 2.5):
                    is_main_tier = True
                    rank = "🏆 本命 (S級)"
                    status_label = "🏆【本命・ブレイク当日】初動適正ブレイク（チェイスなし・バブル排除済）"
                    reason_detail = (
                        f"**【本命S級・高勝率選定理由】**:\n"
                        f"- **出来高倍率**: **{vol_ratio:.2f}倍**（勝ち組特有の1.5〜3.0倍。過熱なし）。\n"
                        f"- **チェイス禁止クリア**: ピボット突破からわずか **{dist_from_pivot:+.2f}%** の初動。\n"
                        f"- **レイトステージ排除済**: 安値上昇率 **{rise_from_low_52w:.1f}%** (基準150%以下)、200日線乖離 **{sma200_bias:+.1f}%** (基準25%以下)。\n"
                        f"- **流動性**: 20日平均売買代金 **{turnover_oku:.1f}億円**（大口機関投資家参入）。\n"
                        f"- **高値圏維持**: 52週高値からわずか **{diff_from_high_52w:+.2f}%**。"
                    )
                # パターンB：ブレイク前夜（VCP売り枯れ・ピボット直下）
                elif raw_near_pivot and (vol_ratio < 1.2) and (-2.5 <= dist_from_pivot <= -0.1):
                    is_main_tier = True
                    rank = "🏆 本命 (S級)"
                    status_label = "🏆【本命・ブレイク前夜】VCP売り枯れ ＆ ピボット直下待機"
                    reason_detail = (
                        f"**【本命S級・高勝率選定理由】**:\n"
                        f"- **売り枯れ確認**: 出来高倍率 **{vol_ratio:.2f}倍**（1.2倍未満の明確な売り枯れ）。\n"
                        f"- **ピボット直下**: ピボット価格から **{dist_from_pivot:+.2f}%** の至近距離。\n"
                        f"- **レイトステージ排除済**: 安値上昇率 **{rise_from_low_52w:.1f}%**、200日線乖離 **{sma200_bias:+.1f}%**。\n"
                        f"- **流動性**: 20日平均売買代金 **{turnover_oku:.1f}億円**。"
                    )
                    
            # ----------------------------------------------------------
            # 🥈 【次点・参考候補A級】判定条件
            # ----------------------------------------------------------
            if not is_main_tier:
                if turnover_oku >= 10.0 and diff_from_high_52w >= -8.0:
                    rank = "🥈 次点 (A級)"
                    geai_note = "【※市場Risk-Off下での逆行高・監視推奨】" if market_status == "Risk-Off" else ""
                    if raw_breakout:
                        status_label = f"🥈【次点・ブレイク当日】モメンタム突破銘柄 {geai_note}"
                        reason_detail = (
                            f"**【次点A級・参考候補理由】**:\n"
                            f"- **地合い状態**: 現在市場は **{market_status}** です。本命買いは見送りですが、逆行高の強い候補として参考表示しています。\n"
                            f"- **ブレイク状況**: 終値 {current_close:.1f}円 がピボット（{pivot_price:.1f}円）を突破（乖離: {dist_from_pivot:+.2f}%）。\n"
                            f"- **レイトステージ排除済**: 安値上昇率 **{rise_from_low_52w:.1f}%**、200日線乖離 **{sma200_bias:+.1f}%**。\n"
                            f"- **出来高倍率**: **{vol_ratio:.2f}倍**、売買代金: **{turnover_oku:.1f}億円**。"
                        )
                    else:
                        status_label = f"🥈【次点・ブレイク前夜】ピボット近傍モミ合い {geai_note}"
                        reason_detail = (
                            f"**【次点A級・参考候補理由】**:\n"
                            f"- **地合い状態**: 現在市場は **{market_status}** です。相場反転時の本命候補としてウォッチリスト推奨です。\n"
                            f"- **株価位置**: ピボット（{pivot_price:.1f}円）から **{dist_from_pivot:+.2f}%**。\n"
                            f"- **レイトステージ排除済**: 安値上昇率 **{rise_from_low_52w:.1f}%**、200日線乖離 **{sma200_bias:+.1f}%**。\n"
                            f"- **出来高倍率**: **{vol_ratio:.2f}倍**、売買代金: **{turnover_oku:.1f}億円**。"
                        )
                        
            if rank is None:
                continue
                
            results.append({
                'ランク': rank,
                'コード': code,
                'ティッカー': ticker,
                '企業名': name,
                '現在値': current_close,
                'ピボット価格': round(pivot_price, 1),
                'ピボット乖離率(%)': round(dist_from_pivot, 2),
                '状態': status_label,
                '出来高倍率': round(vol_ratio, 2),
                '20日平均売買代金(億円)': round(turnover_oku, 2),
                '52週高値乖離率(%)': round(diff_from_high_52w, 2),
                '52週安値上昇率(%)': round(rise_from_low_52w, 2),
                'SMA200乖離率(%)': round(sma200_bias, 2),
                '当日出来高': int(current_vol),
                '20日平均出来高': int(avg_vol_20),
                'SMA50': round(sma50, 1),
                'SMA150': round(sma150, 1),
                'SMA200': round(sma200, 1),
                '52週高値': round(high_52w, 1),
                '52週安値': round(low_52w, 1),
                '💡 抽出理由・根拠詳細': reason_detail
            })
            
        except Exception as e:
            continue
            
    if progress_bar:
        progress_bar.empty()
        
    meta_stats = {
        'total_stocks': total_stock_count,
        'valid_stocks': total_valid,
        'saved_cache_count': len(all_data),
        'cached_count_before': cached_count_before
    }
    return pd.DataFrame(results), meta_stats

def batch_validate_trades(screened_df, signal_date_str, risk_reward_ratio=2.5, progress_bar=None):
    """
    逆指値ピボット突破約定 ＆ ギャップ過熱見送り ＆ リアルスリッページ検証
    """
    if screened_df.empty:
        return pd.DataFrame()
        
    tickers = screened_df['ティッカー'].tolist()
    total = len(tickers)
    
    all_cache = load_local_cache(STOCK_CACHE_FILE)
    missing_tickers = [t for t in tickers if t not in all_cache]
    
    if missing_tickers:
        try:
            target_dt = pd.to_datetime(signal_date_str)
            needed_start_str = (target_dt - timedelta(days=450)).strftime('%Y-%m-%d')
            df_batch = yf.download(missing_tickers, start=needed_start_str, group_by='ticker', threads=True, progress=False)
            if not df_batch.empty:
                for t in missing_tickers:
                    try:
                        if len(missing_tickers) == 1:
                            sub_df = df_batch.dropna(how='all')
                        else:
                            sub_df = df_batch[t].dropna(how='all')
                        if not sub_df.empty:
                            all_cache[t] = merge_stock_df(all_cache.get(t), sub_df)
                    except:
                        continue
                save_local_cache(STOCK_CACHE_FILE, all_cache)
        except Exception:
            pass
            
    validation_results = []
    
    for idx, row in screened_df.iterrows():
        ticker = row['ティッカー']
        code = row['コード']
        name = row['企業名']
        rank = row.get('ランク', '-')
        pivot_price = float(row.get('ピボット価格', 0.0))
        
        if progress_bar:
            prog_val = (idx + 1) / total
            progress_bar.progress(min(prog_val, 1.0), text=f"【{idx + 1}/{total}】 {name} のブレイク推移を追跡検証中...")
            
        df = all_cache.get(ticker)
        if df is None or df.empty:
            continue
            
        try:
            df.index = pd.to_datetime(df.index).strftime('%Y-%m-%d')
            past_df = df[df.index <= signal_date_str]
            future_df = df[df.index > signal_date_str]
            
            if future_df.empty:
                validation_results.append({
                    'ランク': rank,
                    'コード': code,
                    'ティッカー': ticker,
                    '企業名': name,
                    'エントリー日': "翌営業日待ち",
                    '買値(エントリー)': np.nan,
                    '売値(決済/現在値)': np.nan,
                    'SL価格': np.nan,
                    'TP目標': np.nan,
                    '検証ステータス': "⏳ エントリー待機中（データ未到来）",
                    '決済日/現在日': "-",
                    '損益額(円)': 0.0,
                    '損益率(%)': 0.0,
                    '保有日数': 0,
                    '勝敗': "未確定"
                })
                continue
                
            high_low = past_df['High'] - past_df['Low']
            high_cp = np.abs(past_df['High'] - past_df['Close'].shift())
            low_cp = np.abs(past_df['Low'] - past_df['Close'].shift())
            tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
            atr20 = tr.rolling(20).mean().iloc[-1]
            if pd.isna(atr20) or atr20 <= 0:
                atr20 = past_df['Close'].iloc[-1] * 0.02

            breakout_occurred = False
            entry_date = None
            entry_price = None
            skip_status = "🚫 見送り（5日以内未突破・ダマシ事前回避）"
            
            scan_period = future_df.head(5)
            for d_date, d_row in scan_period.iterrows():
                if d_row['High'] >= pivot_price:
                    if d_row['Open'] > pivot_price * 1.05:
                        skip_status = "🚫 見送り（寄り付き5%超ギャップアップ過熱・チェイス禁止）"
                        breakout_occurred = False
                        break
                        
                    breakout_occurred = True
                    entry_date = d_date
                    entry_price = max(d_row['Open'], pivot_price)
                    break
                    
            if not breakout_occurred:
                validation_results.append({
                    'ランク': rank,
                    'コード': code,
                    'ティッカー': ticker,
                    '企業名': name,
                    'エントリー日': "未ブレイク",
                    '買値(エントリー)': np.nan,
                    '売値(決済/現在値)': np.nan,
                    'SL価格': np.nan,
                    'TP目標': np.nan,
                    '検証ステータス': skip_status,
                    '決済日/現在日': "-",
                    '損益額(円)': 0.0,
                    '損益率(%)': 0.0,
                    '保有日数': 0,
                    '勝敗': "見送り"
                })
                continue
                
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
                d_open = d_row['Open']
                
                if d_idx == entry_date:
                    d_high = max(d_high, entry_price)
                    
                hit_sl = d_low <= sl_price
                hit_tp = d_high >= tp_price
                
                if hit_sl and hit_tp:
                    status = "❌ 損切り (同日到達・保守判定)"
                    exit_date = d_idx
                    exit_price = min(d_open, sl_price) if d_open < sl_price else sl_price
                    pnl_amount = exit_price - entry_price
                    pnl_pct = (pnl_amount / entry_price) * 100
                    hold_days = len(trade_period_df.loc[:d_idx])
                    outcome = "負け"
                    break
                elif hit_sl:
                    status = "❌ 損切り (SL到達)"
                    exit_date = d_idx
                    exit_price = min(d_open, sl_price) if d_open < sl_price else sl_price
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
                'ランク': rank,
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