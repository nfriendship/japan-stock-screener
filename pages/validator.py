import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- ページ設定 ---
st.set_page_config(page_title="VCP個別トレード検証アプリ", layout="wide")

# --- ブラック基調の視認性を高めたスタイリッシュなダークテーマCSS ---
st.markdown("""
    <style>
    /* 全体の背景と基本文字色を明るく視認性の高い色に設定 */
    .stApp {
        background-color: #0e1117;
        color: #f0f6fc !important;
    }
    
    /* すべての見出し、通常テキスト、ラベル、説明文の文字色を強制的に明るくする */
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #f0f6fc !important;
    }
    
    /* サイドバー全体の背景と文字色 */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        color: #f0f6fc !important;
    }
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] .stTextInput label {
        color: #f0f6fc !important;
    }
    
    /* メトリック（指標カード）の背景と内部の文字調整 */
    div[data-testid="metric-container"] {
        background-color: #1f242d;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
    }
    div[data-testid="metric-container"] label {
        color: #c9d1d9 !important; /* メトリックの項目名は見やすい明るいグレー */
        font-weight: bold !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #58a6ff !important; /* 数値は鮮やかなブルーで強調 */
    }
    
    /* データフレームの文字や背景の調整 */
    dataframe, table {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 個別銘柄トレード・パフォーマンス検証アプリ")
st.markdown("スクリーニングで抽出された銘柄が、翌日寄り付きエントリーからどう推移したかを検証します。")

# --- サイドバー：入力設定 ---
st.sidebar.header("🔍 検証パラメータ設定")
input_ticker = st.sidebar.text_input("銘柄コード（例: 3101 または 3101.T）", value="3101")
signal_date_str = st.sidebar.text_input("シグナル発生日（YYYY-MM-DD）", value="2026-09-01")

# 利回りの倍率設定（リスクリワード）
risk_reward_ratio = st.sidebar.slider("利確目標のリスク倍率 (RRR)", min_value=1.5, max_value=4.0, value=2.5, step=0.5)

if st.sidebar.button("検証を実行する", type="primary"):
    # ティッカーのフォーマット調整
    ticker = input_ticker.strip()
    if not ticker.endswith(".T"):
        ticker += ".T"
        
    with st.spinner(f"{ticker} のデータを取得して検証中..."):
        try:
            all_df = yf.Ticker(ticker).history(period="2y")
            if all_df.empty:
                st.error("指定された銘柄のデータが取得できませんでした。")
            else:
                all_df.index = pd.to_datetime(all_df.index).strftime('%Y-%m-%d')
                
                # シグナル日までのデータでATRと損切りラインを算出
                past_df = all_df[all_df.index <= signal_date_str]
                if len(past_df) < 20:
                    st.error("シグナル発生日までの過去データが不足しています。")
                else:
                    pivot_price = past_df['High'].tail(20).iloc[:-1].max()
                    high_low = past_df['High'] - past_df['Low']
                    high_cp = np.abs(past_df['High'] - past_df['Close'].shift())
                    low_cp = np.abs(past_df['Low'] - past_df['Close'].shift())
                    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
                    atr20 = tr.rolling(20).mean().iloc[-1]
                    
                    sl_price = max(pivot_price * 0.95, pivot_price - (1.5 * atr20))
                    
                    # 翌営業日の特定
                    future_df = all_df[all_df.index > signal_date_str]
                    if future_df.empty:
                        st.error("シグナル発生日以降の株価データが存在しません。")
                    else:
                        entry_date = future_df.index[0]
                        entry_price = future_df['Open'].iloc[0]
                        
                        risk_amount = entry_price - sl_price
                        tp_price = entry_price + (risk_amount * risk_reward_ratio)
                        
                        st.success(f"**エントリー成功**: {entry_date} の寄り付き **{entry_price:.1f}円** で買い")
                        
                        # メトリクス表示
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("エントリー価格", f"{entry_price:.1f} 円", f"日付: {entry_date}")
                        col2.metric("損切りライン (SL)", f"{sl_price:.1f} 円", f"リスク: -{risk_amount:.1f}円")
                        col3.metric("利確目標 (2.5R)", f"{tp_price:.1f} 円", f"ターゲット: +{risk_amount*risk_reward_ratio:.1f}円")
                        col4.metric("ピボット価格基準", f"{pivot_price:.1f} 円")
                        
                        # シミュレーションループ
                        simulation_data = []
                        status = "保有中 (Active)"
                        exit_date = "-"
                        exit_price = 0.0
                        pnl = 0.0
                        pnl_pct = 0.0
                        
                        trade_period_df = future_df.loc[entry_date:]
                        
                        for idx, row in trade_period_df.iterrows():
                            d_low = row['Low']
                            d_high = row['High']
                            d_close = row['Close']
                            
                            hit_sl = d_low <= sl_price
                            hit_tp = d_high >= tp_price
                            
                            if hit_sl and hit_tp:
                                status = "損切り (Stop Loss Hit - 保守判定)"
                                exit_date = idx
                                exit_price = sl_price
                                pnl = exit_price - entry_price
                                pnl_pct = (pnl / entry_price) * 100
                                simulation_data.append({'日付': idx, '株価(終値)': d_close, '状態': '損切り発動'})
                                break
                            elif hit_sl:
                                status = "損切り (Stop Loss Hit)"
                                exit_date = idx
                                exit_price = sl_price
                                pnl = exit_price - entry_price
                                pnl_pct = (pnl / entry_price) * 100
                                simulation_data.append({'日付': idx, '株価(終値)': d_close, '状態': '損切り発動'})
                                break
                            elif hit_tp:
                                status = "利確達成 (Take Profit Hit)"
                                exit_date = idx
                                exit_price = tp_price
                                pnl = exit_price - entry_price
                                pnl_pct = (pnl / entry_price) * 100
                                simulation_data.append({'日付': idx, '株価(終値)': d_close, '状態': '利確達成'})
                                break
                            else:
                                current_pnl = d_close - entry_price
                                simulation_data.append({'日付': idx, '株価(終値)': d_close, '状態': f'保有中 (含み損益: {current_pnl:+.1f}円)'})
                                exit_price = d_close
                                pnl = current_pnl
                                pnl_pct = (pnl / entry_price) * 100
                        
                        st.markdown("---")
                        st.subheader("📈 トレード結果・ステータス")
                        
                        res_col1, res_col2, res_col3 = st.columns(3)
                        res_col1.metric("現在のステータス", status)
                        res_col2.metric("確定 / 含み損益", f"{pnl:+.1f} 円", f"{pnl_pct:+.2f}%")
                        res_col3.metric("決済日 / 最終確認日", exit_date if exit_date != "-" else trade_period_df.index[-1])
                        
                        # 推移のグラフ化
                        sim_df = pd.DataFrame(simulation_data)
                        if not sim_df.empty:
                            st.subheader("📉 エントリー後の株価推移ログ")
                            st.dataframe(sim_df, use_container_width=True)
                            
                            chart_data = trade_period_df[['Close']].copy()
                            chart_data['Entry'] = entry_price
                            chart_data['StopLoss'] = sl_price
                            chart_data['TakeProfit'] = tp_price
                            st.line_chart(chart_data)
                            
                            # --- CSVエクスポート用データの構築 ---
                            final_exit_date = exit_date if exit_date != '-' else trade_period_df.index[-1]
                            
                            log_lines = []
                            for _, r in sim_df.iterrows():
                                d_date = r['日付']
                                d_val = r['株価(終値)']
                                d_state = r['状態']
                                log_lines.append(f"- {d_date}: 終値 {d_val}円 ({d_state})")
                            log_text = "\n".join(log_lines)
                            
                            summary_text = (
                                f"[銘柄コード]: {ticker}\n"
                                f"[シグナル発生日]: {signal_date_str}\n"
                                f"[エントリー日]: {entry_date}\n"
                                f"[エントリー価格]: {entry_price:.1f}円\n"
                                f"[損切りライン(SL)]: {sl_price:.1f}円\n"
                                f"[利確ターゲット(TP)]: {tp_price:.1f}円\n"
                                f"[最終ステータス]: {status}\n"
                                f"[決済日/最終確認日]: {final_exit_date}\n"
                                f"[最終損益]: {pnl:+.1f}円 ({pnl_pct:+.2f}%)\n"
                                f"[日別推移ログ]:\n{log_text}"
                            )
                            
                            export_df = pd.DataFrame([{
                                '銘柄': ticker,
                                'シグナル日': signal_date_str,
                                '検証結果サマリー（セル内まとめ）': summary_text
                            }])
                            
                            csv_data = export_df.to_csv(index=False).encode('utf-8-sig')
                            
                            st.markdown("---")
                            st.subheader("📥 検証データのダウンロード")
                            st.download_button(
                                label="📊 検証結果サマリーをCSVでダウンロード",
                                data=csv_data,
                                file_name=f"trade_validation_{ticker.replace('.T', '')}_{signal_date_str}.csv",
                                mime="text/csv",
                                help="Excelで開いた際、1つのセル内にすべての検証結果とログが改行されて収まる形式で出力されます。"
                            )
                            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")