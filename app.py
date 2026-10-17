
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="JRA競馬予想AI",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 JRA競馬予想AI")
st.write("全頭評価と買い目提案を目指す競馬予想アプリです。")
st.info("現在は動作確認用のサンプルデータです。実際のJRA出走情報ではありません。")

st.sidebar.header("レース設定")
race_name = st.sidebar.text_input("レース名", "東京 11R")
budget = st.sidebar.number_input(
    "予算（円）",
    min_value=100,
    max_value=100000,
    value=1000,
    step=100
)

st.header(f"📋 {race_name} 全頭評価")

horses = pd.DataFrame({
    "馬番": [1, 2, 3, 4, 5],
    "馬名": [
        "サンプルホースA",
        "サンプルホースB",
        "サンプルホースC",
        "サンプルホースD",
        "サンプルホースE"
    ],
    "近走評価": [90, 82, 75, 70, 65],
    "距離適性": [85, 80, 90, 65, 70],
    "脚質評価": [80, 85, 75, 80, 60]
})

horses["評価点"] = (
    horses["近走評価"] * 0.5
    + horses["距離適性"] * 0.3
    + horses["脚質評価"] * 0.2
).round(1)

horses = horses.sort_values("評価点", ascending=False).reset_index(drop=True)

def mark(position):
    marks = ["◎", "○", "▲", "△", "☆"]
    return marks[position] if position < len(marks) else ""

horses["印"] = [mark(i) for i in range(len(horses))]

st.dataframe(
    horses[["馬番", "馬名", "評価点", "印"]],
    use_container_width=True,
    hide_index=True
)

st.header("🎯 買い目提案（試作）")
st.write(f"設定予算：{budget:,}円")
st.write("評価上位の馬を候補として表示します。")

top_horses = horses.head(3)
st.write("評価上位：" + "、".join(top_horses["馬名"].tolist()))

st.warning(
    "この評価は仮の数値によるデモです。"
    "実際の出走馬データやオッズに基づく予想ではありません。"
)

st.caption("JRA競馬予想AI 試作版")
