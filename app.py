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
    </style>
""", unsafe_allow_html=True)

st.title("📈 株式買い候補銘柄 自動抽出システム")
st.markdown("東証の主要個別銘柄（ETF除外）に基づき、アルゴリズムでブレイクアウト銘柄を抽出します。")

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
    st.warning(f"【市場環境：Risk-Off】 {market_msg}")
else:
    st.info(f"【市場環境：Neutral】 {market_msg}")

st.markdown("---")

# --- スクリーニング実行 ---
if st.button("指定日でのスクリーニングを実行する", type="primary"):
    progress_bar = st.progress(0, text="市場データを取得準備中...")
    
    with st.spinner("東証個別銘柄リストを準備中..."):
        stock_df = get_tse_stock_list()
        
    with st.spinner("スクリーニングを実行中..."):
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
        st.info(f"📊 **審査母数**: 東証の実在個別株 **{meta.get('valid_stocks', 0)} 銘柄** の株価データを正常に審査完了（うち既存キャッシュ利用: **{meta.get('cached_count_before', 0)} 銘柄**）")
        
    st.subheader(f"📋 買い候補銘柄一覧（判定日: {d_str} / 該当数: {len(res_df)}件）")
    
    if res_df.empty:
        st.warning("条件に一致する銘柄は見つかりませんでした。")
    else:
        display_cols = ['コード', '企業名', '現在値', 'ピボット価格', '状態', '出来高倍率', '20日平均売買代金(億円)']
        st.dataframe(res_df[display_cols], use_container_width=True)
        
        st.markdown("### 🔍 各銘柄の選定理由・根拠の詳細確認")
        for idx, row in res_df.iterrows():
            with st.expander(f"【{row['コード']}】 {row['企業名']} （現在値: {row['現在値']}円 / 出来高倍率: {row['出来高倍率']}倍 / 売買代金: {row['20日平均売買代金(億円)']}億円）"):
                st.markdown(row['💡 抽出理由・根拠詳細'])
                
        # --- スクリーニング単体のCSVダウンロード ---
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
        # ⚡ 自動一括トレード検証（バックテスト）セクション
        # ==============================================================
        st.markdown("---")
        st.subheader("⚡ 抽出銘柄のトレード結果・一括検証")
        st.markdown("抽出された全銘柄について、**翌営業日寄り付きでエントリーした後の売買結果・現在の含み損益** を検証します。")
        
        v_col1, v_col2 = st.columns([1, 2])
        with v_col1:
            rrr = st.slider("利確目標のリスク倍率 (RRR)", min_value=1.5, max_value=4.0, value=2.5, step=0.5, key="batch_rrr")
        with v_col2:
            st.caption("※ 損切りライン(SL)はピボット価格とATR(20)から自動設定されます（買値より下を完全保証）。同日両到達時は保守的に損切り優先と判定します。")
            
        if st.button("🚀 この抽出銘柄のトレード結果を一括検証する"):
            v_progress = st.progress(0, text="抽出銘柄の推移データを取得中...")
            val_df = batch_validate_trades(res_df, d_str, risk_reward_ratio=rrr, progress_bar=v_progress)
            st.session_state['val_df'] = val_df
            st.session_state['val_d_str'] = d_str
            st.rerun()
            
        if 'val_df' in st.session_state:
            val_df = st.session_state['val_df']
            
            if val_df.empty:
                st.warning("検証対象のデータがありませんでした。")
            else:
                pending_count = len(val_df[val_df['検証ステータス'].str.contains("未到来|待機中")])
                
                if pending_count == len(val_df):
                    st.info(f"⏳ **検証結果**: 設定判定日（{d_str}）以降の相場データが存在しないため、全銘柄が**翌営業日の寄り付き待ち（待機中）**です。")
                    st.dataframe(val_df[['コード', '企業名', '検証ステータス']], use_container_width=True)
                else:
                    finished_trades = val_df[val_df['勝敗'].isin(['勝ち', '負け'])]
                    win_trades = val_df[val_df['勝敗'] == '勝ち']
                    
                    win_rate = (len(win_trades) / len(finished_trades) * 100) if len(finished_trades) > 0 else 0.0
                    avg_pnl = val_df['損益率(%)'].mean()
                    total_pnl_yen = val_df['損益額(円)'].sum()
                    active_count = len(val_df[val_df['勝敗'] == '保有中'])
                    
                    st.markdown("#### 📊 パフォーマンス集計サマリー")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("検証銘柄数", f"{len(val_df)} 銘柄")
                    m2.metric("勝率（決済済み）", f"{win_rate:.1f} %", f"{len(win_trades)}勝 / {len(finished_trades)}決済")
                    m3.metric("全銘柄 平均損益率", f"{avg_pnl:+.2f} %")
                    m4.metric("現在保有中（含み推移）", f"{active_count} 銘柄", f"合計損益: {total_pnl_yen:+.1f}円")
                    
                    st.markdown("#### 📋 銘柄別トレード結果一覧（売買価格・損益詳細）")
                    val_display_cols = [
                        'コード', '企業名', 'エントリー日', '買値(エントリー)', '売値(決済/現在値)', 
                        'SL価格', 'TP目標', '検証ステータス', '決済日/現在日', '損益額(円)', '損益率(%)', '保有日数'
                    ]
                    st.dataframe(val_display_cols, use_container_width=True)
                    
                    val_subset = val_df.drop(columns=['企業名', 'ティッカー'], errors='ignore')
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