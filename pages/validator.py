import streamlit as pd_st # Streamlitの競合を防ぐため別名にしてもよいが通常通りimport
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="VCP個別トレード検証アプリ", layout="wide")

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
            # 余裕を持って過去データ＋未来データを取得するため期間を広げる
            df = yf.Ticker(ticker).history(period="1y")
            if df.empty:
                st.error("指定された銘柄のデータが取得できませんでした。")
            else:
                df.index = pd.to_datetime(df.index).strftime('%Y-%m-%d')
                
                # シグナル発生日以降のデータに絞る
                # まず、シグナル発生日以前のデータからATRやピボットを計算するための親データフレームが必要
                # ここでは簡易的にシグナル発生日のデータを特定
                all_df = yf.Ticker(ticker).history(period="2y")
                all_df.index = pd.to_datetime(all_df.index).strftime('%Y-%m-%d')
                
                # シグナル日までのデータでATRと損切りラインを算出
                past_df = all_df[all_df.index <= signal_date_str]
                if len(past_df) < 20:
                    st.error("シグナル発生日までの過去データが不足しています。")
                else:
                    # スクリーニングロジックと同様の損切り計算
                    pivot_price = past_df['High'].tail(20).iloc[:-1].max()
                    high_low = past_df['High'] - past_df['Low']
                    high_cp = np.abs(past_df['High'] - past_df['Close'].shift())
                    low_cp = np.abs(past_df['Low'] - past_df['Close'].shift())
                    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
                    atr20 = tr.rolling(20).mean().iloc[-1]
                    
                    sl_price = max(pivot_price * 0.95, pivot_price - (1.5 * atr20))
                    
                    # 翌営業日の特定（シグナル日より後の最初の日）
                    future_df = all_df[all_df.index > signal_date_str]
                    if future_df.empty:
                        st.error("シグナル発生日以降の株価データが存在しません。")
                    else:
                        entry_date = future_df.index[0]
                        entry_price = future_df['Open'].iloc[0]
                        
                        # リスク幅と利確ターゲットの算出
                        risk_amount = entry_price - sl_price
                        tp_price = entry_price + (risk_amount * risk_reward_ratio)
                        
                        st.success(f"**エントリー成功**: {entry_date} の寄り付き **{entry_price:.1f}円** で買い")
                        
                        # メトリクス表示
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("エントリー価格", f"{entry_price:.1f} 円", f"日付: {entry_date}")
                        col2.metric("損切りライン (SL)", f"{sl_price:.1f} 円", f"リスク: -{risk_amount:.1f}円")
                        col3.metric(番付 := f"利確目標 ({risk_reward_ratio}R)", f"{tp_price:.1f} 円", f"ターゲット: +{risk_amount*risk_reward_ratio:.1f}円")
                        col4.metric("ピボット価格基準", f"{pivot_price:.1f} 円")
                        
                        # シミュレーションループ（日ごとの追跡）
                        simulation_data = []
                        status = "保有中 (Active)"
                        exit_date = "-"
                        exit_price = 0.0
                        pnl = 0.0
                        pnl_pct = 0.0
                        
                        # エントリー日以降のデータを走査
                        trade_period_df = future_df.loc[entry_date:]
                        
                        for idx, row in trade_period_df.iterrows():
                            d_low = row['Low']
                            d_high = row['High']
                            d_close = row['Close']
                            
                            # 判定順序：同日中に両方タッチした場合は保守的に損切り優先、あるいは日足ベースの判定
                            hit_sl = d_low <= sl_price
                            hit_tp = d_high >= tp_price
                            
                            if hit_sl and hit_tp:
                                status = "損切り (Stop Loss Hit - 同時ヒット時保守判定)"
                                exit_date = idx
                                exit_price = sl_price
                                pnl = exit_price - entry_price
                                pnl_pct = (pnl / entry_price) * 100
                                simulation_data.append({'日付': idx, '株価(終値)': d_close, '状態': '損切り発動'})
                                break
                            elif hit_sl:
                                status = "損切り (Stop Loss Hit)"
                                exit_date = idx
                                exit_price = sl_price # 実際は窓開け下落リスクもあるがライン到達で計算
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
                                # 継続中
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
                            
                            # チャート表示
                            chart_data = trade_period_df[['Close']].copy()
                            chart_data['Entry'] = entry_price
                            chart_data['StopLoss'] = sl_price
                            chart_data['TakeProfit'] = tp_price
                            st.line_chart(chart_data)
                            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")