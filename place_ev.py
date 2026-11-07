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
            col2.metric(
                "収録馬数",
                f"{history_data['血統登録番号'].replace('', pd.NA).nunique():,}"
            )
            col3.metric("学習対象行数", f"{len(valid_data):,}")
            col4.metric(
                "3着内実績",
                f"{int((valid_data['3着内実績'] == 1).sum()):,}"
            )

            st.success("過去成績CSVを読み込みました。")

            st.write("着順データの確認")
            finish_summary = (
                valid_data["確定着順"]
                .value_counts()
                .sort_index()
                .rename_axis("確定着順")
                .reset_index(name="頭数")
            )
            st.dataframe(
                finish_summary,
                use_container_width=True,
                hide_index=True
            )

            st.write("過去成績のサンプル")
            preview_columns = [
                "開催日", "競馬場", "レース番号", "馬番", "馬名",
                "騎手名", "距離", "馬場状態", "確定着順",
                "人気順", "単勝オッズ", "上がり3Fタイム",
                "父馬名", "母馬名", "母の父馬名", "3着内実績"
            ]
            st.dataframe(
                valid_data[preview_columns].head(30),
                use_container_width=True,
                hide_index=True
            )

            # 学習用の正解ラベル付きデータをCSVで保存できる
            training_csv = valid_data.to_csv(
                index=False
            ).encode("utf-8-sig")
            st.download_button(
                "学習用データ（着順ラベル付き）をCSV保存",
                data=training_csv,
                file_name="target_training_labels.csv",
                mime="text/csv"
            )

            st.caption(
                "注意：この段階では過去の着順を正解ラベルにしただけです。"
                "AIの学習・予測はまだ行っていません。"
            )

    except Exception as e:
        st.error(f"過去成績CSVの読み込みでエラーが発生しました：{e}")


st.divider()

# ---------------------------------------------------------
# ② 当日出馬表CSVの読み込み
# ---------------------------------------------------------
st.subheader("② TARGET出馬表CSV")

uploaded_file = st.file_uploader(
    "TARGETの出馬表CSVを選択（例：DE261107.CSV）",
    type=["csv"],
    key="entries_csv"
)

imported_data = None

if uploaded_file is not None:
    try:
        raw = read_target_csv(uploaded_file)

        if raw.shape[1] < 22:
            st.error("出馬表CSVの列数が不足しています。")
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
                f"出馬表CSV読み込み成功！ 出走馬数：{len(imported_data)}頭"
            )

            st.subheader("③ 開催全体の集計")
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

            st.subheader("④ レースごとの出走馬")
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

            st.subheader("⑤ 全馬の期待値分析")
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

            st.subheader("⑥ 複勝期待値ランキング")
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
                    result_df = pd.DataFrame(results)
                    result_df = result_df.sort_values(
                        ["保守的期待値", "中央値期待値"],
                        ascending=False
                    ).reset_index(drop=True)
                    result_df.insert(0, "順位", range(1, len(result_df) + 1))

                    st.dataframe(
                        result_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    candidates = result_df[
                        result_df["保守的期待値"] > threshold
                    ]

                    col1, col2 = st.columns(2)
                    col1.metric("分析した馬", len(result_df))
                    col2.metric("買い候補", len(candidates))

                    if len(candidates) > 0:
                        st.success("期待値の基準を満たした馬")
                        st.dataframe(
                            candidates,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.warning("条件を満たす馬はいません。")

                    csv = result_df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        "ランキングをCSV保存",
                        data=csv,
                        file_name="place_ev_ranking.csv",
                        mime="text/csv"
                    )

    except Exception as e:
        st.error(f"出馬表CSVの読み込みでエラーが発生しました：{e}")
else:
    st.info("TARGETの出馬表CSVをアップロードすると、開催・レース別の確認ができます。")
