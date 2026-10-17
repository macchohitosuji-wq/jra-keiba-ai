
import streamlit as st
import pandas as pd

st.set_page_config(page_title="JRA競馬予想AI", page_icon="🏇", layout="wide")

st.title("🏇 JRA競馬予想AI")
st.write("全頭評価と買い目提案を目指す開発版です。")
st.info("現在は手入力式です。実際のJRAデータやAI予測とは連携していません。")

st.sidebar.header("レース設定")
race_name = st.sidebar.text_input("レース名", "東京 11R")
budget = st.sidebar.number_input(
    "予算（円）", min_value=100, max_value=100000,
    value=1000, step=100
)

st.header("📋 出走馬データ")
st.caption("各評価を0〜100点で入力してください。配点に基づいて総合評価を計算します。")

sample = pd.DataFrame({
    "馬番": [1, 2, 3, 4, 5],
    "馬名": ["サンプルA", "サンプルB", "サンプルC", "サンプルD", "サンプルE"],
    "近走成績": [90, 82, 75, 70, 65],
    "距離適性": [85, 80, 90, 65, 70],
    "脚質・展開": [80, 85, 75, 80, 60],
    "血統適性": [80, 75, 85, 70, 65],
    "調教評価": [85, 80, 75, 70, 65],
    "馬場適性": [80, 85, 75, 70, 65],
})

weights = {
    "近走成績": 0.35,
    "距離適性": 0.20,
    "脚質・展開": 0.15,
    "血統適性": 0.10,
    "調教評価": 0.10,
    "馬場適性": 0.10,
}

horses = st.data_editor(
    sample,
    num_rows="dynamic",
    use_container_width=True,
    key="horse_editor",
    column_config={
        "馬番": st.column_config.NumberColumn("馬番", min_value=1, step=1),
        "馬名": st.column_config.TextColumn("馬名"),
        **{
            col: st.column_config.NumberColumn(
                col, min_value=0, max_value=100, step=1
            )
            for col in weights
        },
    },
)

st.subheader("評価配点")
st.write("近走成績35%・距離適性20%・脚質と展開15%・血統10%・調教10%・馬場10%")

if not horses.empty:
    horses = horses.copy()

    for col in weights:
        horses[col] = pd.to_numeric(horses[col], errors="coerce")

    horses["評価点"] = sum(
        horses[col] * weight for col, weight in weights.items()
    ).round(1)

    horses = horses.dropna(subset=["評価点", "馬名"])
    horses = horses.sort_values("評価点", ascending=False).reset_index(drop=True)

    marks = ["◎", "○", "▲", "△", "☆"]
    horses["印"] = [
        marks[i] if i < len(marks) else ""
        for i in range(len(horses))
    ]

    st.header(f"🏆 {race_name} 全頭評価")
    st.dataframe(
        horses[["馬番", "馬名", "評価点", "印"]],
        use_container_width=True,
        hide_index=True,
    )

    st.header("🎯 買い目候補")
    st.write(f"予算：{budget:,}円")
    st.write("評価上位馬：" + "、".join(
        horses.head(3)["馬名"].astype(str).tolist()
    ))
    st.warning(
        "買い目候補は評価点の上位馬を示すだけです。"
        "馬券の組み合わせや購入金額はまだ自動最適化していません。"
    )
else:
    st.info("出走馬を1頭以上入力してください。")

st.caption("JRA競馬予想AI 試作版")
