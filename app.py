import streamlit as st
import pandas as pd
from datetime import datetime
from screener import get_tse_stock_list, analyze_market, run_screener_batch

# --- ページ設定 ---
st.set_page_config(page_title="日本株VCP・ブレイクアウトスクリーニングシステム", layout="wide")

# --- 視認性とデザインを最適化したダークテーマCSS ---
st.markdown("""
    <style>
    /* 全体の背景と基本文字色 */
    .stApp {
        background-color: #0e1117;
        color: #f0f6fc;
    }
    
    /* メインエリア内の見出しやテキストを明るく */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp label {
        color: #f0f6fc !important;
    }
    
    /* 右上のヘッダー（Stop、Deploy、点3つボタンなど）の背景を黒くし、文字を白くする */
    header[data-testid="stHeader"] {
        background-color: #0e1117 !important;
    }
    header[data-testid="stHeader"] * {
        color: #f0f6fc !important;
    }
    
    /* サイドバー全体の背景と文字色 */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        color: #f0f6fc !important;
    }
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] span {
        color: #f0f6fc !important;
    }
    
    /* 【超重要】サイドバー内の入力ボックス（日付・テキスト）の視認性対策 */
    /* 背景を白、文字色をはっきりとした黒に固定 */
    section[data-testid="stSidebar"] input,
    div[data-testid="stDateInput"] input,
    div[data-baseweb="input"] input {
        background-color: #ffffff !important;
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
        font-weight: 600 !important;
    }

    /* 入力ボックスの外枠コンテナの文字色・背景色も同期 */
    div[data-baseweb="input"] {
        background-color: #ffffff !important;
    }
    
    /* CSVダウンロードボタンの視認性改善 */
    div.stDownloadButton > button {
        background-color: #238636 !important;
        color: #ffffff !important;
        border: 1px solid #3fb950 !important;
        font-weight: bold !important;
        border-radius: 6px;
    }
    div.stDownloadButton > button:hover {
        background-color: #2ea043 !important;
        border-color: #56d364 !important;
    }
    
    /* データフレームやテーブルの調整 */
    dataframe, table {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
    }
    
    /* エキスパンダーの調整 */
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
st.markdown("指定した日付時点の株価データに基づき、アルゴリズムでブレイクアウト銘柄を抽出します。")

# --- サイドバー：実行設定 ---
st.sidebar.header("⚙ 実行設定")
target_date = st.sidebar.date_input("判定基準日（この日までのデータで判定）", value=datetime.today().date())
target_date_str = target_date.strftime('%Y-%m-%d')

st.info(f"📅 設定中の判定日: **{target_date_str}**")

# --- 市場環境判定の表示 ---
market_status, market_msg = analyze_market(target_date_str)
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
    
    with st.spinner("銘柄リストを取得中..."):
        stock_df = get_tse_stock_list()
        
    with st.spinner("スクリーニングを実行中..."):
        result_df = run_screener_batch(stock_df, target_date_str, progress_bar)
        
    progress_bar.empty()
    st.success("解析が完了しました！")
    
    # セッションステートに結果を保存
    st.session_state['result_df'] = result_df
    st.session_state['target_date_str'] = target_date_str

# --- 結果の表示 ---
if 'result_df' in st.session_state:
    res_df = st.session_state['result_df']
    d_str = st.session_state.get('target_date_str', target_date_str)
    
    st.subheader(f"📋 買い候補銘柄一覧（判定日: {d_str} / 該当数: {len(res_df)}件）")
    
    if res_df.empty:
        st.warning("条件に一致する銘柄は見つかりませんでした。")
    else:
        # 画面表示用のテーブル（抽出理由は除外）
        display_df = res_df.drop(columns=['💡 抽出理由・根拠詳細'])
        st.dataframe(display_df, use_container_width=True)
        
        st.markdown("### 🔍 各銘柄の選定理由・根拠の詳細確認")
        for idx, row in res_df.iterrows():
            with st.expander(f"【{row['コード']}】 {row['企業名']} （現在値: {row['現在値']}円 / 出来高倍率: {row['出来高倍率']}倍）"):
                st.markdown(row['💡 抽出理由・根拠詳細'])
                
        # --- CSVダウンロード（判定日を左端列に挿入） ---
        export_df = res_df.copy()
        export_df.insert(0, '判定日', d_str)
        csv = export_df.to_csv(index=False).encode('utf-8-sig')
        
        st.markdown("---")
        st.subheader("📥 抽出結果データのダウンロード")
        st.download_button(
            label="📊 抽出結果と理由をCSVでダウンロード",
            data=csv,
            file_name=f"vcp_screening_result_{d_str}.csv",
            mime="text/csv"
        )