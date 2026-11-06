import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="複勝期待値AI",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 複勝期待値AI")
st.caption("TARGET出馬表の取り込み・レース別集計・複勝期待値分析")

st.info(
    "現在は出走馬データの取り込みと集計に対応しています。"
    "3着内確率のAI予測は今後追加します。"
)

# ① CSV読み込み
st.subheader("① TARGET出馬表CSV")

uploaded_file = st.file_uploader(
    "TARGETの出馬表CSVを選択",
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
            st.error("CSVの列数が不足しています。")
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

            st.success(
                f"CSV読み込み成功！ 出走馬数：{len(imported_data)}頭"
            )

            # ② 全体集計
            st.subheader("② 開催全体の集計")

            venue_summary = (
                imported_data.groupby("競馬場")
                .agg(
                    レース数=("レース", "nunique"),
                    出走馬数=("馬名", "count")
                )
                .reset_index()
            )

            race_summary = (
                imported_data.groupby(
                    ["競馬場", "レース"],
                    sort=False
                )
                .agg(
                    出走頭数=("馬名", "count"),
                    クラス=("クラス", "first"),
                    コース=("コース", "first"),
                    距離=("距離", "first")
                )
                .reset_index()
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("競馬場数", imported_data["競馬場"].nunique())
            col2.metric("レース数", len(race_summary))
            col3.metric("出走馬数", len(imported_data))

            st.write("競馬場別集計")
            st.dataframe(
                venue_summary,
                use_container_width=True,
                hide_index=True
            )

            st.write("レース別出走頭数")
            st.dataframe(
                race_summary,
                use_container_width=True,
                hide_index=True
            )

            # ③ レース選択
            st.subheader("③ レースごとの出走馬")

            race_options = (
                race_summary["競馬場"]
                + " "
                + race_summary["レース"]
            ).tolist()

            selected_race = st.selectbox(
                "確認したいレースを選択",
                race_options
            )

            selected_venue, selected_number = selected_race.rsplit(" ", 1)

            selected_horses = imported_data[
                (imported_data["競馬場"] == selected_venue)
                & (imported_data["レース"] == selected_number)
            ].copy()

            st.write(
                f"{selected_venue} {selected_number} "
                f"出走頭数：{len(selected_horses)}頭"
            )

            st.dataframe(
                selected_horses[
                    [
                        "馬番", "馬名", "性別", "年齢",
                        "騎手", "斤量", "クラス",
                        "コース", "距離", "父", "母", "母父"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            # ④ 期待値計算用データ
            st.subheader("④ 全馬の期待値分析")

            default_data = imported_data[
                ["競馬場", "レース", "馬番", "馬名"]
            ].copy()

            default_data["3着内確率(%)"] = 0.0
            default_data["オッズ下限"] = 1.0
            default_data["オッズ上限"] = 1.0

            horses = st.data_editor(
                default_data,
                num_rows="dynamic",
                use_container_width=True,
                key=f"horse_editor_{uploaded_file.name}",
                column_config={
                    "3着内確率(%)": st.column_config.NumberColumn(
                        min_value=0.0,
                        max_value=100.0,
                        format="%.1f"
                    ),
                    "オッズ下限": st.column_config.NumberColumn(
                        min_value=1.0
                    ),
                    "オッズ上限": st.column_config.NumberColumn(
                        min_value=1.0
                    ),
                }
            )

            st.caption(
                "確率とオッズは現在手入力です。"
                "CSVを読み込んだだけではAI予測値にはなりません。"
            )

            # ⑤ 期待値ランキング
            st.subheader("⑤ 複勝期待値ランキング")

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
                            errors.append(f"{name}: 確率を確認してください")
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
                            "判定": (
                                "候補" if p * low > threshold
                                else "見送り"
                            )
                        })

                    except (ValueError, TypeError, KeyError):
                        errors.append(
                            f"{index + 1}行目: 入力内容を確認してください"
                        )

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
                        df,
                        use_container_width=True,
                        hide_index=True
                    )

                    candidates = df[
                        df["保守的期待値"] > threshold
                    ]

                    col1, col2 = st.columns(2)
                    col1.metric("分析した馬", len(df))
                    col2.metric("買い候補", len(candidates))

                    if len(candidates) > 0:
                        st.success("期待値の基準を満たした馬")
                        st.dataframe(
                            candidates,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.warning(
                            "条件を満たす馬はいません。"
                        )

                    csv = df.to_csv(
                        index=False
                    ).encode("utf-8-sig")

                    st.download_button(
                        "ランキングをCSV保存",
                        data=csv,
                        file_name="place_ev_ranking.csv",
                        mime="text/csv"
                    )

    except Exception as e:
        st.error(f"エラーが発生しました：{e}")

else:
    st.info("TARGETのCSVをアップロードすると分析が始まります。")
