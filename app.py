import streamlit as st
import pandas as pd
from datetime import datetime
from screener import (
    get_tse_stock_list, analyze_market, run_screener_batch, 
    batch_validate_trades, clear_all_cache, load_local_cache, STOCK_CACHE_FILE
)

# --- ページ設定 ---
st.set_page_config(page_title="日本株VCP・ブレイクアウトスクリーニングシステム", layout="wide")

# --- 視認性とデザインを最適化したダークテーマCSS ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #f0f6fc;
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p {
        color: #f0f6fc !important;
    }
    header[data-testid="stHeader"] {
        background-color: #0e1117 !important;
    }
    header[data-testid="stHeader"] * {
        color: #f0f6fc !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        color: #f0f6fc !important;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] label p,
    section[data-testid="stSidebar"] label span,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
    div[data-testid="stDateInput"] label,
    div[data-testid="stDateInput"] label * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stDateInput"] {
        background-color: transparent !important;
    }
    div[data-testid="stDateInput"] div[data-baseweb="input"],
    div[data-testid="stDateInput"] div[data-baseweb="base-input"] {
        background-color: #ffffff !important;
    }
    div[data-testid="stDateInput"] input {
        background-color: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        font-weight: 700 !important;
    }
    div[data-testid="metric-container"] {
        background-color: #1f242d;
        border: 1px solid #30363d;
        padding: 12px;
        border-radius: 8px;
    }
    div[data-testid="metric-container"] label {
        color: #c9d1d9 !important;
        font-weight: bold !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
    }
    div[data-testid="stButton"] button,
    div.stButton button {
        background-color: #1f6feb !important;
        background: #1f6feb !important;
        border: 1px solid #388bfd !important;
        border-radius: 6px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4) !important;
    }
    div[data-testid="stButton"] button:hover,
    div.stButton button:hover {
        background-color: #388bfd !important;
        border-color: #58a6ff !important;
    }
    div[data-testid="stButton"] button *,
    div.stButton button * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: bold !important;
    }
    div[data-testid="stButton"] button[kind="primary"],
    div.stButton button[kind="primary"] {
        background-color: #ff4b4b !important;
        background: #ff4b4b !important;
        border: 1px solid #ff6b6b !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #ff6b6b !important;
    }
    div[data-testid="stButton"] button[kind="primary"] *,
    div.stButton button[kind="primary"] * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: bold !important;
    }
    div[data-testid="stDownloadButton"] button,
    div[data-testid="stDownloadButton"] a,
    div.stDownloadButton button,
    div.stDownloadButton a {
        background-color: #238636 !important;
        background: #238636 !important;
        border: 1px solid #3fb950 !important;
        border-radius: 6px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4) !important;
    }
    div[data-testid="stDownloadButton"] button:hover,
    div.stDownloadButton button:hover {
        background-color: #2ea043 !important;
        border-color: #56d364 !important;
    }
    div[data-testid="stDownloadButton"] *,
    div.stDownloadButton * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: bold !important;
    }
    dataframe, table {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
    }
    details {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px;
        padding: 5px;
    }
    details summary p {
        color: #58a6ff !important;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #161b22;
        border-radius: 6px 6px 0 0;
        color: #c9d1d9;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #21262d !important;
        color: #58a6ff !important;
        font-weight: bold;
        border-bottom: 2px solid #58a6ff !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 株式買い候補銘柄 自動抽出システム")
st.markdown("ビッグデータ検証に基づく **「本命S級（過熱・バブル排除）」** と **「逆指値ピボット突破約定」** を備えたプロ仕様システムです。")

# --- サイドバー：実行設定 ＆ キャッシュ操作 ---
st.sidebar.header("⚙ 実行設定")
target_date = st.sidebar.date_input("判定基準日（この日までのデータで判定）", value=datetime.today().date())
target_date_str = target_date.strftime('%Y-%m-%d')

st.sidebar.markdown("---")
st.sidebar.subheader("💾 データ取得・キャッシュ設定")
data_mode = st.sidebar.radio(
    "取得モード",
    ["⚡ 高速キャッシュ優先（バックテスト推奨）", "🔄 ライブ最新データを強制取得（更新）"],
    index=0,
    help="「高速キャッシュ優先」を選択すると、不足している期間のみを自動でダウンロードして既存データと結合し、不要な通信を完全遮断します。"
)
use_cache = "高速キャッシュ優先" in data_mode

current_cache = load_local_cache(STOCK_CACHE_FILE)
cached_count_display = st.session_state.get('saved_cache_count', len(current_cache))
st.sidebar.caption(f"📦 現在保存中のキャッシュ: **{cached_count_display} 銘柄分**")

if st.sidebar.button("🗑 キャッシュを全消去して初期化"):
    clear_all_cache()
    if 'saved_cache_count' in st.session_state:
        del st.session_state['saved_cache_count']
    st.sidebar.success("キャッシュを消去しました。")
    st.rerun()

st.info(f"📅 設定中の判定日: **{target_date_str}** ｜ モード: **{'⚡ キャッシュ高速実行' if use_cache else '🔄 ライブ通信更新'}**")

# --- 市場環境判定の表示 ---
market_status, market_msg = analyze_market(target_date_str, use_cache=use_cache)
if "Risk-On" in market_status:
    st.success(f"【市場環境：Risk-On】 {market_msg}")
elif "Risk-Off" in market_status:
    st.error(f"【市場環境：Risk-Off】 {market_msg} ⚠️ ブレイクアウトのダマシ確率が極めて高いため、本命銘柄であっても買いは見送りを強く推奨します。")
else:
    st.warning(f"【市場環境：Neutral】 {market_msg} ⚠️ トレンドの方向感が曖昧なため、厳選した本命S級のみに絞るか、ロットを落としたトレードを推奨します。")

st.markdown("---")

# --- スクリーニング実行 ---
if st.button("指定日でのスクリーニングを実行する", type="primary"):
    progress_bar = st.progress(0, text="市場データを取得準備中...")
    
    with st.spinner("東証個別銘柄リストを準備中..."):
        stock_df = get_tse_stock_list()
        
    with st.spinner("アルゴリズム解析を実行中..."):
        result_df, meta_stats = run_screener_batch(stock_df, target_date_str, use_cache=use_cache, progress_bar=progress_bar)
        
    progress_bar.empty()
    st.success("解析が完了しました！")
    
    st.session_state['result_df'] = result_df
    st.session_state['meta_stats'] = meta_stats
    st.session_state['target_date_str'] = target_date_str
    st.session_state['saved_cache_count'] = meta_stats.get('saved_cache_count', 0)
    if 'val_df' in st.session_state:
        del st.session_state['val_df']
    st.rerun()

# --- 結果の表示 ---
if 'result_df' in st.session_state:
    res_df = st.session_state['result_df']
    d_str = st.session_state.get('target_date_str', target_date_str)
    meta = st.session_state.get('meta_stats', {})
    
    if meta:
        st.info(f"📊 **審査母数**: 東証の実在個別株 **{meta.get('valid_stocks', 0)} 銘柄** を審査（うち既存キャッシュ利用: **{meta.get('cached_count_before', 0)} 銘柄**）")
        
    if res_df.empty:
        st.warning("厳格なスクリーニング条件に一致する銘柄は見つかりませんでした。")
    else:
        main_df = res_df[res_df['ランク'].str.contains('本命')]
        sub_df = res_df[res_df['ランク'].str.contains('次点')]
        
        st.subheader(f"📋 買い候補銘柄一覧（判定日: {d_str} ｜ 合計: {len(res_df)}件）")
        
        tab1, tab2, tab3 = st.tabs([
            f"🏆 本命・高勝率S級 ({len(main_df)}件)",
            f"🥈 次点・参考候補A級 ({len(sub_df)}件)",
            f"📑 全一覧 ({len(res_df)}件)"
        ])
        
        display_cols = ['ランク', 'コード', '企業名', '現在値', 'ピボット価格', '状態', '出来高倍率', '20日平均売買代金(億円)', '52週高値乖離率(%)', '52週安値上昇率(%)', 'SMA200乖離率(%)']
        
        with tab1:
            if main_df.empty:
                st.info("※ この判定日における本命S級銘柄はありませんでした。")
            else:
                st.dataframe(main_df[display_cols], use_container_width=True)
                st.markdown("#### 🔍 本命S級の選定理由・詳細")
                for _, row in main_df.iterrows():
                    with st.expander(f"【{row['コード']}】 {row['企業名']} （現在値: {row['現在値']}円 / 出来高: {row['出来高倍率']}倍 / 代金: {row['20日平均売買代金(億円)']}億円 / 200日線乖離: {row['SMA200乖離率(%)']:+.1f}%）"):
                        st.markdown(row['💡 抽出理由・根拠詳細'])
                        
        with tab2:
            if sub_df.empty:
                st.info("※ 次点A級銘柄はありませんでした。")
            else:
                st.dataframe(sub_df[display_cols], use_container_width=True)
                st.markdown("#### 🔍 次点A級の選定理由・詳細")
                for _, row in sub_df.iterrows():
                    with st.expander(f"【{row['コード']}】 {row['企業名']} （現在値: {row['現在値']}円 / 出来高: {row['出来高倍率']}倍 / 代金: {row['20日平均売買代金(億円)']}億円）"):
                        st.markdown(row['💡 抽出理由・根拠詳細'])
                        
        with tab3:
            st.dataframe(res_df[display_cols], use_container_width=True)
            
        export_df = res_df.copy()
        export_df.insert(0, '判定日', d_str)
        csv_screening = export_df.to_csv(index=False).encode('utf-8-sig')
        
        st.download_button(
            label="📊 スクリーニング結果（全指標入り）をCSVダウンロード",
            data=csv_screening,
            file_name=f"vcp_screening_result_{d_str}.csv",
            mime="text/csv"
        )
        
        # ==============================================================
        # ⚡ 逆指値ピボット突破約定トレード検証セクション
        # ==============================================================
        st.markdown("---")
        st.subheader("⚡ 抽出銘柄のトレード結果・一括検証（逆指値ブレイク約定方式）")
        st.markdown("判定日以降、**ピボット価格を上抜けた瞬間（逆指値）に約定した銘柄のみを追跡検証**します（抜けずに下落した銘柄は「見送り」として損切りを未然回避）。")
        
        v_col1, v_col2 = st.columns([1, 2])
        with v_col1:
            rrr = st.slider("利確目標のリスク倍率 (RRR)", min_value=1.5, max_value=4.0, value=2.5, step=0.5, key="batch_rrr")
        with v_col2:
            st.caption("※ 損切りライン(SL)はピボット価格とATR(20)から自動設定。5営業日以内にピボットを突破しなかった銘柄はノー・トレードとして除外されます。")
            
        if st.button("🚀 この抽出銘柄のトレード結果を一括検証する"):
            v_progress = st.progress(0, text="抽出銘柄のブレイク推移を追跡検証中...")
            val_df = batch_validate_trades(res_df, d_str, risk_reward_ratio=rrr, progress_bar=v_progress)
            st.session_state['val_df'] = val_df
            st.session_state['val_d_str'] = d_str
            st.rerun()
            
        if 'val_df' in st.session_state:
            val_df = st.session_state['val_df']
            
            if val_df.empty:
                st.warning("検証対象のデータがありませんでした。")
            else:
                pending_count = len(val_df[val_df['検証ステータス'].str.contains("待機中")])
                
                if pending_count == len(val_df):
                    st.info(f"⏳ **検証結果**: 設定判定日（{d_str}）以降の相場データが存在しないため、全銘柄が**待機中**です。")
                    st.dataframe(val_df[['ランク', 'コード', '企業名', '検証ステータス']], use_container_width=True)
                else:
                    finished_trades = val_df[val_df['勝敗'].isin(['勝ち', '負け'])]
                    win_trades = val_df[val_df['勝敗'] == '勝ち']
                    loss_trades = val_df[val_df['勝敗'] == '負け']
                    skipped_count = len(val_df[val_df['勝敗'] == '見送り'])
                    active_count = len(val_df[val_df['勝敗'] == '保有中'])
                    
                    win_rate = (len(win_trades) / len(finished_trades) * 100) if len(finished_trades) > 0 else 0.0
                    avg_pnl = finished_trades['損益率(%)'].mean() if len(finished_trades) > 0 else 0.0
                    
                    # プロフィットファクター（PF）の計算
                    total_win_yen = win_trades['損益額(円)'].sum() if not win_trades.empty else 0.0
                    total_loss_yen = abs(loss_trades['損益額(円)'].sum()) if not loss_trades.empty else 0.0
                    pf = (total_win_yen / total_loss_yen) if total_loss_yen > 0 else (99.9 if total_win_yen > 0 else 0.0)
                    
                    # 本命 vs 次点の勝率比較
                    main_val = val_df[val_df['ランク'].str.contains('本命')]
                    main_finished = main_val[main_val['勝敗'].isin(['勝ち', '負け'])]
                    main_wins = main_val[main_val['勝敗'] == '勝ち']
                    main_win_rate = (len(main_wins) / len(main_finished) * 100) if len(main_finished) > 0 else 0.0
                    
                    sub_val = val_df[val_df['ランク'].str.contains('次点')]
                    sub_finished = sub_val[sub_val['勝敗'].isin(['勝ち', '負け'])]
                    sub_wins = sub_val[sub_val['勝敗'] == '勝ち']
                    sub_win_rate = (len(sub_wins) / len(sub_finished) * 100) if len(sub_finished) > 0 else 0.0
                    
                    st.markdown("#### 📊 パフォーマンス集計サマリー")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("総抽出 / 約定決済", f"{len(val_df)} 銘柄", f"{len(finished_trades)} 決済 (🚫見送り: {skipped_count}件)")
                    m2.metric("🏆 本命S級 勝率", f"{main_win_rate:.1f} %", f"{len(main_wins)}勝 / {len(main_finished)}決済")
                    m3.metric("🥈 次点A級 勝率", f"{sub_win_rate:.1f} %", f"{len(sub_wins)}勝 / {len(sub_finished)}決済")
                    m4.metric("プロフィットファクター (PF)", f"{pf:.2f}", f"決済平均損益: {avg_pnl:+.2f}%")
                    
                    st.markdown("#### 📋 銘柄別トレード結果一覧（売買価格・損益詳細）")
                    val_display_cols = [
                        'ランク', 'コード', '企業名', 'エントリー日', '買値(エントリー)', '売値(決済/現在値)', 
                        'SL価格', 'TP目標', '検証ステータス', '決済日/現在日', '損益額(円)', '損益率(%)', '保有日数'
                    ]
                    st.dataframe(val_df[val_display_cols], use_container_width=True)
                    
                    val_subset = val_df.drop(columns=['企業名', 'ティッカー', 'ランク'], errors='ignore')
                    merged_export = pd.merge(export_df, val_subset, on='コード', how='left')
                    
                    csv_merged = merged_export.to_csv(index=False).encode('utf-8-sig')
                    
                    st.markdown("---")
                    st.subheader("📥 スクリーニング指標 ＆ 売買結果の完全突合CSV")
                    st.download_button(
                        label="📊 全テクニカル指標 ＆ トレード結果の完全突合CSVをダウンロード",
                        data=csv_merged,
                        file_name=f"vcp_trade_validation_merged_{d_str}.csv",
                        mime="text/csv",
                        help="スクリーニング時の全指標と実際の売買結果が1行に結合されたCSVです。"
                    )