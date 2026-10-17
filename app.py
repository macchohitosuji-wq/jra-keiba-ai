import streamlit as st
import pandas as pd

st.set_page_config(page_title="JRA競馬予想AI", page_icon="🏇", layout="wide")

st.title("🏇 JRA競馬予想AI")
st.write("出走馬を入力して、全頭評価と買い目候補を作成します。")
st.info("現在は手入力版です。実際のJRA出走情報は自動取得していません。")

st.sidebar.header("レース設定")
race_name = st.sidebar.text_input("レース名", "東京 11R")
budget = st.sidebar.number_input(
    "予算（円）", min_value=100, max_value=100000,
    value=1000, step=100
)

st.header("出走馬データ")
st.caption("馬名や各評価を編集できます。評価は0〜100点で入力してください。")

sample = pd.DataFrame({
    "馬番": [1, 2, 3, 4, 5],
    "馬名": ["サンプルA", "サンプルB", "サンプルC", "サンプルD", "サンプルE"],
    "近走評価": [90, 82, 75, 70, 65],
    "距離適性": [85, 80, 90, 65, 70],
    "脚質評価": [80, 85, 75, 80, 60],
})

horses = st.data_editor(
    sample,
    num_rows="dynamic",
    use_container_width=True,
    key="horse_editor",
    column_config={
        "馬番": st.column_config.NumberColumn("馬番", min_value=1, step=1),
        "馬名": st.column_config.TextColumn("馬名"),
        "近走評価": st.column_config.NumberColumn("近走評価", min_value=0, max_value=100),
        "距離適性": st.column_config.NumberColumn("距離適性", min_value=0, max_value=100),
        "脚質評価": st.column_config.NumberColumn("脚質評価", min_value=0, max_value=100),
    },
)

if not horses.empty:
    horses = horses.copy()
    score_columns = ["近走評価", "距離適性", "脚質評価"]

    for col in score_columns:
        horses[col] = pd.to_numeric(horses[col], errors="coerce")

    horses["評価点"] = (
        horses["近走評価"] * 0.5
        + horses["距離適性"] * 0.3
        + horses["脚質評価"] * 0.2
    ).round(1)

    horses = horses.dropna(subset=["評価点", "馬名"])
    horses = horses.sort_values("評価点", ascending=False).reset_index(drop=True)

    marks = ["◎", "○", "▲", "△", "☆"]
    horses["印"] = [
        marks[i] if i < len(marks) else ""
        for i in range(len(horses))
    ]

    st.header(f"📋 {race_name} 全頭評価")
    st.dataframe(
        horses[["馬番", "馬名", "評価点", "印"]],
        use_container_width=True,
        hide_index=True,
    )

    st.header("🎯 買い目候補")
    st.write(f"予算：{budget:,}円")
    st.write("評価上位馬：" + "、".join(horses.head(3)["馬名"].astype(str).tolist()))
    st.warning("評価点は入力値から計算した参考値です。的中や利益を保証するものではありません。")
else:
    st.info("出走馬を1頭以上入力してください。")
