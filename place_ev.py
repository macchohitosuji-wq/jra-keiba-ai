import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="複勝期待値AI",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 複勝期待値AI")
st.caption("TARGET出馬表・過去成績の取り込みと複勝期待値分析")

st.info(
    "現在はTARGETデータの取り込みと学習用ラベルの作成段階です。"
    "表示される3着内ラベルは実際の過去着順であり、AI予測値ではありません。"
)

# TARGET「成績データCSV形式仕様」のフルセット52項目
HISTORY_COLUMNS = [
    "年", "月", "日", "回次", "競馬場", "日次", "レース番号",
    "レース名", "クラスコード", "芝・ダ", "トラックコード", "距離",
    "馬場状態", "馬名", "性別", "年齢", "騎手名", "斤量", "頭数",
    "馬番", "確定着順", "入線着順", "異常コード", "着差タイム",
    "人気順", "走破タイム", "走破時計", "補正タイム", "通過順1",
    "通過順2", "通過順3", "通過順4", "上がり3Fタイム", "馬体重",
    "調教師", "所属地", "賞金", "血統登録番号", "騎手コード",
    "調教師コード", "レースID", "馬主名", "生産者名", "父馬名",
    "母馬名", "母の父馬名", "毛色", "生年月日", "単勝オッズ",
    "馬印", "レース印", "PCI"
]


def read_target_csv(uploaded_file):
    """TARGETのCSVを文字列として読み込む。"""
    try:
        uploaded_file.seek(0)
        return pd.read_csv(
            uploaded_file,
            header=None,
            dtype=str,
            encoding="cp932"
        )
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(
            uploaded_file,
            header=None,
            dtype=str,
            encoding="utf-8-sig"
        )


def clean_text_columns(df):
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df


# ---------------------------------------------------------
# ① 過去成績CSVの読み込み
# ---------------------------------------------------------
st.subheader("① TARGET過去成績CSV（フルセット＋単オッズ）")

history_file = st.file_uploader(
    "全馬成績CSVを選択（例：DS261107.CSV）",
    type=["csv"],
    key="history_csv"
)

history_data = None

if history_file is not None:
    try:
        history_raw = read_target_csv(history_file)

        if history_raw.shape[1] != 52:
            st.error(
                f"列数が52列ではありません。今回のフルセット形式は52列です。"
                f" 読み込み列数：{history_raw.shape[1]}列"
            )
        else:
            history_data = history_raw.copy()
            history_data.columns = HISTORY_COLUMNS
            history_data = clean_text_columns(history_data)

            # 数値化できない値は欠損として扱う
            numeric_columns = [
                "年", "月", "日", "回次", "日次", "レース番号",
                "クラスコード", "トラックコード", "距離", "年齢",
                "斤量", "頭数", "馬番", "確定着順", "入線着順",
                "異常コード", "着差タイム", "人気順", "走破タイム",
                "走破時計", "補正タイム", "通過順1", "通過順2",
                "通過順3", "通過順4", "上がり3Fタイム", "馬体重",
                "賞金", "単勝オッズ", "PCI"
            ]
            for col in numeric_columns:
                history_data[col] = pd.to_numeric(
                    history_data[col].replace("", pd.NA),
                    errors="coerce"
                )

            # 年月日を作成（TARGETの年は西暦下2桁）
            history_data["開催日"] = pd.to_datetime(
                {
                    "year": 2000 + history_data["年"].fillna(0).astype(int),
                    "month": history_data["月"].fillna(1).astype(int),
                    "day": history_data["日"].fillna(1).astype(int),
                },
                errors="coerce"
            )

            # 確定着順と異常コードから、学習用の正解ラベルを作る
            # 異常コード0かつ確定着順1～18のレースだけを対象にする
            valid_result = (
                history_data["確定着順"].notna()
                & history_data["確定着順"].between(1, 18)
                & (history_data["異常コード"] == 0)
            )

            history_data["3着内実績"] = pd.NA
            history_data.loc[valid_result, "3着内実績"] = (
                history_data.loc[valid_result, "確定着順"] <= 3
            ).astype(int)

            valid_data = history_data.loc[valid_result].copy()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("過去成績行数", f"{len(history_data):,}")
