import streamlit as st
import pandas as pd
from datetime import date
from screener import get_tse_stock_list, analyze_market, run_screener_batch

st.set_page_config(page_title="株式VCPブレイクアウト・スクリーナー", layout="wide")

st.title("📈 株式買い候補銘柄 自動抽出システム")
st.caption("指定した日付時点の株価データに基づき、アルゴリズムでブレイクアウト銘柄を抽出します。")

# --- 日付選択サイドバー ---
st.sidebar.header("⚙️ 実行設定")
target_date = st.sidebar.date_input(
    "判定基準日（この日までのデータで判定）",
    value=date.today(),
    max_value=date.today()
)
target_date_str = target_date.strftime('%Y-%m-%d')

st.info(f"📅 設定中の判定日: **{target_date_str}**")

# 市場環境判定
market_status, market_msg = analyze_market(target_date_str)
if market_status == "Risk-On":
    st.success(f"【市場環境：{market_status}】 {market_msg}")
elif market_status == "Neutral":
    st.warning(f"【市場環境：{market_status}】 {market_msg}")
else:
    st.error(f"【市場環境：{market_status}】 {market_msg}")

st.divider()

# スクリーニング実行ボタン
if st.button("指定日でのスクリーニングを実行する", type="primary"):
    with st.spinner("東証銘柄マスターを取得中..."):
        stock_df = get_tse_stock_list()
    
    if not stock_df.empty:
        progress_bar = st.progress(0, text="処理を開始します...")
        results_df = run_screener_batch(stock_df, target_date_str, progress_bar)
        progress_bar.empty()
        
        st.session_state['results_df'] = results_df
        st.session_state['executed_date'] = target_date_str
        st.success("解析が完了しました！")
    else:
        st.error("銘柄リストの取得に失敗しました。")

# 結果表示エリア
if 'results_df' in st.session_state:
    df = st.session_state['results_df']
    exec_date = st.session_state.get('executed_date', '')
    st.subheader(f"📋 買い候補銘柄一覧（判定日: {exec_date} / 該当数: {len(df)}件）")
    
    if not df.empty:
        # 表全体の表示（'銘柄名' を '企業名' に変更対応）
        summary_df = df[['コード', '企業名', '業種', '現在値', 'ピボット価格', '損切り目安', '出来高倍率']]
        st.dataframe(summary_df, use_container_width=True)
        
        st.divider()
        st.subheader("🔍 各銘柄の選定理由・根拠の詳細確認")
        
        # 銘柄ごとにアコーディオン形式で詳細な理由を表示
        for _, row in df.iterrows():
            with st.expander(f"【{row['コード']}】 {row['企業名']} （現在値: {row['現在値']}円 / 出来高倍率: {row['出来高倍率']}倍）"):
                st.markdown(row['💡 抽出理由・根拠詳細'])
                
        # CSVダウンロードボタン
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="抽出結果と理由をCSVでダウンロード",
            data=csv,
            file_name=f"buy_candidates_{exec_date}.csv",
            mime="text/csv",
        )
    else:
        st.info("指定された日付において、すべての買い条件（トレンド・流動性・ブレイクアウト）を満たした銘柄はありませんでした。")