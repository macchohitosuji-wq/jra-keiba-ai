import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(
    page_title="複勝期待値AI",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 複勝期待値AI")
st.caption("TARGETの出馬表CSVを読み込み、全出走馬を分析する開発版")

st.info(
    "現在は出走馬データの取り込みと手入力による期待値計算に対応しています。"
    "AIによる3着内確率の予測機能は今後追加します。"
)

st.subheader("① TARGETの出馬表CSVを読み込む")

uploaded_file = st.file_uploader(
    "DE261107.CSVなどの出馬表CSVを選択",
    type=["csv"]
)

imported_data = None

if uploaded_file is not None:
    try:
        try:
            raw = pd.read_csv(
                uploaded_file,
                header=None,
                dtype=str,
                encoding="cp932"
            )
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            raw = pd.read_csv(
                uploaded_file,
                header=None,
                dtype=str,
                encoding="utf-8-sig"
            )

        if raw.shape[1] < 22:
            st.error("CSVの列数が想定より少ないため、形式を確認する必要があります。")
        else:
            imported_data = pd.DataFrame({
                "開催日": raw.iloc[:, 0].str.strip(),
                "競馬場": raw.iloc[:, 1].str.strip(),
                "レース": raw.iloc[:, 2].str.strip() + "R",
                "馬番": raw.iloc[:, 3].str.strip(),
                "クラス": raw.iloc[:, 4].str.strip(),
                "コース": raw.iloc[:, 5].str.strip(),
                "距離": raw.iloc[:, 6].str.strip(),
                "馬名": raw.iloc[:, 7].str.strip(),
                "性別": raw.iloc[:, 8].str.strip(),
                "年齢": raw.iloc[:, 9].str.strip(),
                "騎手": raw.iloc[:, 10].str.strip(),
                "斤量": raw.iloc[:, 11].str.strip(),
                "調教師": raw.iloc[:, 12].str.strip(),
                "父": raw.iloc[:, 16].str.strip(),
                "母": raw.iloc[:, 17].str.strip(),
                "馬ID": raw.iloc[:, 18].str.strip(),
                "母父": raw.iloc[:, 20].str.strip(),
            })

            imported_data = imported_data[
                imported_data["馬名"].notna()
                & (imported_data["馬名"] != "")
            ].copy()

            imported_data["3着内確率(%)"] = 0.0
            imported_data["オッズ下限"] = 1.0
            imported_data["オッズ上限"] = 1.0

            st.success(
                f"CSVを読み込みました！ 出走馬数：{len(imported_data)}頭"
            )

            st.write("読み込んだ出走馬データ")
            st.dataframe(
                imported_data[
                    ["競馬場", "レース", "馬番", "馬名",
                     "騎手", "斤量", "父", "母", "母父"]
                ],
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました：{e}")

st.divider()

st.subheader("② 期待値計算用データ")

if imported_data is not None and len(imported_data) > 0:
    default_data = imported_data[
        ["競馬場", "レース", "馬番", "馬名",
         "3着内確率(%)", "オッズ下限", "オッズ上限"]
    ].copy()
else:
    st.caption("CSVを読み込むか、以下のテストデータを使用できます。")
    default_data = pd.DataFrame([
        {"競馬場": "東京", "レース": "1R", "馬番": "1",
         "馬名": "テスト馬1", "3着内確率(%)": 60.0,
         "オッズ下限": 1.5, "オッズ上限": 2.0},
        {"競馬場": "東京", "レース": "1R", "馬番": "2",
         "馬名": "テスト馬2", "3着内確率(%)": 50.0,
         "オッズ下限": 2.0, "オッズ上限": 2.5},
    ])

horses = st.data_editor(
    default_data,
    num_rows="dynamic",
    use_container_width=True,
    key="horse_editor",
    column_config={
        "3着内確率(%)": st.column_config.NumberColumn(
            min_value=0.0, max_value=100.0, format="%.1f"
        ),
        "オッズ下限": st.column_config.NumberColumn(min_value=1.0),
        "オッズ上限": st.column_config.NumberColumn(min_value=1.0),
    }
)

st.caption(
    "3着内確率と複勝オッズは、現段階では手入力です。"
    "CSVから取り込んだだけではAI予測値にはなりません。"
)

st.subheader("③ 期待値ランキング")

threshold = st.number_input(
    "買い候補にする保守的期待値",
    min_value=0.0,
    value=1.0,
    step=0.05
)

if st.button("🏇 全馬の期待値を計算", type="primary"):
    results = []
    errors = []

    for index, horse in horses.iterrows():
        try:
            name = str(horse["馬名"]).strip()
            if not name:
                continue

            p = float(horse["3着内確率(%)"]) / 100
            low = float(horse["オッズ下限"])
            high = float(horse["オッズ上限"])

            if not 0 <= p <= 1:
                errors.append(f"{name}: 確率が範囲外です")
                continue

            if low < 1 or high < low:
                errors.append(f"{name}: オッズを確認してください")
                continue

            mid = (low + high) / 2

            results.append({
                "競馬場": horse["競馬場"],
                "レース": horse["レース"],
                "馬番": horse["馬番"],
                "馬名": name,
                "3着内確率(%)": p * 100,
                "複勝下限": low,
                "複勝上限": high,
                "保守的期待値": p * low,
                "中央値期待値": p * mid,
                "上限期待値": p * high,
                "判定": "候補" if p * low > threshold else "見送り"
            })

        except (ValueError, TypeError, KeyError):
            errors.append(f"{index + 1}行目: 入力内容を確認してください")

    for error in errors:
        st.error(error)

    if results:
        df = pd.DataFrame(results)
        df = df.sort_values(
            ["保守的期待値", "中央値期待値"],
            ascending=False
        ).reset_index(drop=True)

        df.insert(0, "順位", range(1, len(df) + 1))

        st.dataframe(
            df.style.format({
                "3着内確率(%)": "{:.1f}%",
                "複勝下限": "{:.2f}",
                "複勝上限": "{:.2f}",
                "保守的期待値": "{:.3f}",
                "中央値期待値": "{:.3f}",
                "上限期待値": "{:.3f}",
            }),
            use_container_width=True,
            hide_index=True
        )

        candidates = df[df["保守的期待値"] > threshold]

        col1, col2 = st.columns(2)
        col1.metric("分析した馬", len(df))
        col2.metric("買い候補", len(candidates))

        if len(candidates) > 0:
            st.success("期待値の基準を満たした馬")
            st.dataframe(candidates, use_container_width=True, hide_index=True)
        else:
            st.warning("条件を満たす馬はいません。")

        csv = df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "ランキングをCSV保存",
            data=csv,
            file_name="place_ev_ranking.csv",
            mime="text/csv"
        )
