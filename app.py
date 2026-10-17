
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="JRA競馬予想AI",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 JRA競馬予想AI")
st.write("全頭評価と買い目提案を目指す開発版です。")
st.info(
    "現在は手入力とCSV読み込みに対応しています。"
    "実際のJRAデータやAI予測とは連携していません。"
)

st.sidebar.header("レース設定")

race_name = st.sidebar.text_input("レース名", "東京 11R")

budget = st.sidebar.number_input(
    "予算（円）",
    min_value=100,
    max_value=100000,
    value=1000,
    step=100
)

weights = {
    "近走成績": 0.35,
    "距離適性": 0.20,
    "脚質・展開": 0.15,
    "血統適性": 0.10,
    "調教評価": 0.10,
    "馬場適性": 0.10,
}

columns = [
    "馬番", "馬名", "近走成績", "距離適性",
    "脚質・展開", "血統適性", "調教評価", "馬場適性"
]

sample = pd.DataFrame({
    "馬番": [1, 2, 3, 4, 5],
    "馬名": [
        "サンプルA", "サンプルB", "サンプルC",
        "サンプルD", "サンプルE"
    ],
    "近走成績": [90, 82, 75, 70, 65],
    "距離適性": [85, 80, 90, 65, 70],
    "脚質・展開": [80, 85, 75, 80, 60],
    "血統適性": [80, 75, 85, 70, 65],
    "調教評価": [85, 80, 75, 70, 65],
    "馬場適性": [80, 85, 75, 70, 65],
})

st.header("📂 出走馬CSV読み込み")
st.write(
    "CSVファイルをアップロードすると、"
    "そのデータを使って評価できます。"
)

uploaded_file = st.file_uploader(
    "出走馬データCSV",
    type=["csv"]
)

if uploaded_file is not None:
    try:
        try:
            uploaded_file.seek(0)
            loaded = pd.read_csv(
                uploaded_file, encoding="utf-8-sig"
            )
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            loaded = pd.read_csv(
                uploaded_file, encoding="cp932"
            )

        # 列名の前後の空白を除去
        loaded.columns = loaded.columns.astype(str).str.strip()

        missing = [col for col in columns if col not in loaded.columns]

        if missing:
            st.error(
                "CSVに必要な列がありません：" + "、".join(missing)
            )
            st.caption(
                "下のサンプルCSVを参考に、列名を合わせてください。"
            )
            horses_input = sample.copy()
        else:
            horses_input = loaded[columns].copy()
            st.success(
                f"CSVを読み込みました。{len(horses_input)}頭"
            )

    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました：{e}")
        horses_input = sample.copy()
else:
    horses_input = sample.copy()
    st.caption(
        "CSVをアップロードしない場合は、サンプルデータから始められます。"
    )

st.download_button(
    label="📥 サンプルCSVをダウンロード",
    data=sample.to_csv(index=False).encode("utf-8-sig"),
    file_name="jra_horses_sample.csv",
    mime="text/csv"
)

st.header("📋 出走馬データ")
st.caption(
    "各評価を0〜100点で入力してください。"
    "CSVを読み込んだ場合も、ここで修正できます。"
)

horses = st.data_editor(
    horses_input,
    num_rows="dynamic",
    use_container_width=True,
    key="horse_editor",
    column_config={
        "馬番": st.column_config.NumberColumn(
            "馬番", min_value=1, step=1
        ),
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
st.write(
    "近走成績35%・距離適性20%・脚質と展開15%・"
    "血統10%・調教10%・馬場10%"
)

if not horses.empty:
    horses = horses.copy()

    horses["馬名"] = horses["馬名"].fillna("").astype(str).str.strip()

    for col in weights:
        horses[col] = pd.to_numeric(horses[col], errors="coerce")

    horses["評価点"] = sum(
        horses[col] * weight
        for col, weight in weights.items()
    ).round(1)

    horses = horses.dropna(subset=["評価点", "馬番"])
    horses = horses[horses["馬名"] != ""]

    horses = horses.sort_values(
        "評価点", ascending=False
    ).reset_index(drop=True)

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

    top_horses = horses.head(3)["馬名"].astype(str).tolist()

    if top_horses:
        st.write("評価上位馬：" + "、".join(top_horses))
    else:
        st.info("有効な出走馬データを入力してください。")

    st.warning(
        "評価点は入力データと設定した配点に基づく計算値です。"
        "的中を保証するものではなく、"
        "馬券の組み合わせや購入金額も自動最適化していません。"
    )
else:
    st.info("出走馬を1頭以上入力してください。")

st.caption("JRA競馬予想AI 試作版")
