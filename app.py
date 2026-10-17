
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

st.divider()
st.header("📊 STEP 17：予想とレース結果の照合")

st.write(
    "確定着順CSVを読み込み、今回の予想と実際の結果を比較します。"
)

# 結果CSVのサンプル
sample_results = pd.DataFrame({
    "馬番": [1, 2, 3, 4, 5],
    "着順": [3, 1, 5, 4, 2],
})

st.download_button(
    label="📥 結果CSVのサンプルをダウンロード",
    data=sample_results.to_csv(
        index=False
    ).encode("utf-8-sig"),
    file_name="jra_results_sample.csv",
    mime="text/csv",
)

st.caption(
    "CSVには「馬番」「着順」の列が必要です。"
    "着順には1、2、3…の確定順位を入力してください。"
)

result_file = st.file_uploader(
    "確定着順CSVをアップロード",
    type=["csv"],
    key="result_csv_uploader",
)

if result_file is not None:
    try:
        try:
            result_file.seek(0)
            results = pd.read_csv(
                result_file, encoding="utf-8-sig"
            )
        except UnicodeDecodeError:
            result_file.seek(0)
            results = pd.read_csv(
                result_file, encoding="cp932"
            )

        results.columns = (
            results.columns.astype(str).str.strip()
        )

        required = ["馬番", "着順"]
        missing = [
            col for col in required
            if col not in results.columns
        ]

        if missing:
            st.error(
                "結果CSVに必要な列がありません："
                + "、".join(missing)
            )

        elif horses.empty or "評価点" not in horses.columns:
            st.error(
                "先に出走馬データを入力してください。"
            )

        else:
            results["馬番"] = pd.to_numeric(
                results["馬番"], errors="coerce"
            )
            results["着順"] = pd.to_numeric(
                results["着順"], errors="coerce"
            )

            results = results.dropna(
                subset=["馬番", "着順"]
            )

            if results["馬番"].duplicated().any():
                st.error(
                    "結果CSVに重複した馬番があります。"
                    "1頭につき1行にしてください。"
                )
            else:
                predictions = horses[
                    ["馬番", "馬名", "評価点", "印"]
                ].copy()

                predictions["馬番"] = pd.to_numeric(
                    predictions["馬番"],
                    errors="coerce"
                )

                comparison = predictions.merge(
                    results[["馬番", "着順"]],
                    on="馬番",
                    how="inner",
                    validate="one_to_one"
                )

                if comparison.empty:
                    st.warning(
                        "予想データと結果CSVで"
                        "一致する馬番がありません。"
                    )
                else:
                    comparison = comparison.sort_values(
                        "評価点", ascending=False
                    )

                    st.success(
                        f"{len(comparison)}頭の結果を照合しました。"
                    )

                    st.subheader("照合結果")

                    st.dataframe(
                        comparison[
                            ["馬番", "馬名", "評価点", "印", "着順"]
                        ].sort_values("着順"),
                        use_container_width=True,
                        hide_index=True,
                    )

                    # ◎の実際の着順
                    honmei = comparison[
                        comparison["印"] == "◎"
                    ]

                    if not honmei.empty:
                        honmei_finish = honmei.iloc[0]["着順"]

                        st.metric(
                            "◎の確定着順",
                            f"{int(honmei_finish)}着"
                        )

                        if honmei_finish <= 3:
                            st.success(
                                "◎は3着以内に入りました。"
                            )
                        else:
                            st.info(
                                "◎は3着以内に入りませんでした。"
                            )

                    # 評価上位3頭のうち実際に3着以内だった頭数
                    top3 = comparison.head(3)
                    hits = int((top3["着順"] <= 3).sum())

                    st.metric(
                        "評価上位3頭の複勝圏入り",
                        f"{hits} / {len(top3)}頭"
                    )

                    st.caption(
                        "これは今回1レースの結果です。"
                        "長期的な的中率・回収率を示すものではありません。"
                        "回収率の計算には実際の購入額と払戻額も必要です。"
                    )

    except Exception as e:
        st.error(f"結果CSVの読み込みに失敗しました：{e}")


st.divider()
st.header("📚 STEP 18：検証記録・成績集計")

st.write(
    "レースごとの検証結果をCSVに保存し、"
    "あとから読み込んで複数レースの成績を集計できます。"
)

record_columns = [
    "レース名",
    "馬番",
    "馬名",
    "評価点",
    "印",
    "着順",
]

# 今回の検証結果を記録用CSVに変換
if (
    "comparison" in locals()
    and isinstance(comparison, pd.DataFrame)
    and not comparison.empty
):
    current_records = comparison[
        ["馬番", "馬名", "評価点", "印", "着順"]
    ].copy()

    current_records.insert(0, "レース名", race_name)

    current_records = current_records[record_columns]

    st.download_button(
        label="📥 今回の検証記録をダウンロード",
        data=current_records.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name="jra_race_record.csv",
        mime="text/csv",
        key="download_current_record",
    )
else:
    st.info(
        "先にSTEP 17で確定着順CSVを読み込むと、"
        "今回の検証記録をダウンロードできます。"
    )

st.subheader("📂 過去の検証記録を読み込む")

history_file = st.file_uploader(
    "過去の検証記録CSV",
    type=["csv"],
    key="history_csv_uploader",
)

if history_file is not None:
    try:
        try:
            history_file.seek(0)
            history = pd.read_csv(
                history_file, encoding="utf-8-sig"
            )
        except UnicodeDecodeError:
            history_file.seek(0)
            history = pd.read_csv(
                history_file, encoding="cp932"
            )

        history.columns = (
            history.columns.astype(str).str.strip()
        )

        missing_history = [
            col for col in record_columns
            if col not in history.columns
        ]

        if missing_history:
            st.error(
                "記録CSVに必要な列がありません："
                + "、".join(missing_history)
            )
        else:
            history = history[record_columns].copy()

            history["着順"] = pd.to_numeric(
                history["着順"], errors="coerce"
            )

            history["評価点"] = pd.to_numeric(
                history["評価点"], errors="coerce"
            )

            history = history.dropna(
                subset=["着順", "評価点"]
            )

            st.success(
                f"{len(history)}頭分の記録を読み込みました。"
            )

            st.subheader("📈 複数レースの成績")

            race_count = history["レース名"].nunique()

            st.metric(
                "記録されたレース数",
                f"{race_count}レース"
            )

            # 各レースの◎を集計対象にする
            honmei = history[history["印"] == "◎"]

            if not honmei.empty:
                honmei_hits = int(
                    (honmei["着順"] <= 3).sum()
                )

                honmei_rate = (
                    honmei_hits / len(honmei) * 100
                )

                st.metric(
                    "◎の3着以内率",
                    f"{honmei_rate:.1f}%",
                    f"{honmei_hits}/{len(honmei)}頭"
                )
            else:
                st.info("◎の記録がありません。")

            # 各レースの評価上位3頭を抽出
            top3_records = (
                history.sort_values(
                    ["レース名", "評価点"],
                    ascending=[True, False]
                )
                .groupby("レース名", sort=False)
                .head(3)
            )

            if not top3_records.empty:
                top3_hits = int(
                    (top3_records["着順"] <= 3).sum()
                )

                top3_rate = (
                    top3_hits / len(top3_records) * 100
                )

                st.metric(
                    "評価上位3頭の3着以内率",
                    f"{top3_rate:.1f}%",
                    f"{top3_hits}/{len(top3_records)}頭"
                )

            st.subheader("記録一覧")

            st.dataframe(
                history.sort_values(
                    ["レース名", "評価点"],
                    ascending=[True, False]
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "同じレース名を複数回記録すると同一レースとして集計されます。"
                "別のレースは区別できる名前を付けてください。"
                "記録はCSVをダウンロードして保管してください。"
                "この集計は入力された記録に基づくもので、"
                "将来の的中を保証するものではありません。"
            )

    except Exception as e:
        st.error(
            f"検証記録の読み込みに失敗しました：{e}"
        )


st.divider()
st.header("💰 STEP 18-2：馬券収支・回収率の記録")

st.write(
    "レースごとの実際の購入額と払戻額を入力し、"
    "収支・回収率を計算します。"
)

st.caption(
    "購入額・払戻額は実際の金額を入力してください。"
    "購入しなかったレースは登録しないでください。"
)

with st.form("bet_record_form"):
    bet_race_name = st.text_input(
        "レース名",
        placeholder="例：2026-10-18 秋華賞"
    )

    bet_amount = st.number_input(
        "購入額（円）",
        min_value=100,
        max_value=1000000,
        value=1000,
        step=100
    )

    payout_amount = st.number_input(
        "払戻額（円）",
        min_value=0,
        max_value=100000000,
        value=0,
        step=100
    )

    save_bet = st.form_submit_button(
        "収支を計算"
    )

if save_bet:
    if not bet_race_name.strip():
        st.error("レース名を入力してください。")
    elif bet_amount <= 0:
        st.error("購入額は0円より大きくしてください。")
    else:
        profit = int(payout_amount - bet_amount)
        recovery = payout_amount / bet_amount * 100

        st.subheader("今回の収支")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "購入額",
            f"{bet_amount:,}円"
        )

        col2.metric(
            "払戻額",
            f"{payout_amount:,}円"
        )

        col3.metric(
            "収支",
            f"{profit:+,}円"
        )

        st.metric(
            "回収率",
            f"{recovery:.1f}%"
        )

        # ダウンロードできる記録CSVを作成
        bet_record = pd.DataFrame([{
            "レース名": bet_race_name.strip(),
            "購入額": int(bet_amount),
            "払戻額": int(payout_amount),
            "収支": profit,
            "回収率(%)": round(recovery, 1),
        }])

        st.download_button(
            label="📥 この収支記録をCSV保存",
            data=bet_record.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="jra_bet_record.csv",
            mime="text/csv",
            key="download_bet_record",
        )

        if profit > 0:
            st.success("今回はプラス収支です。")
        elif profit < 0:
            st.warning("今回はマイナス収支です。")
        else:
            st.info("今回は収支が±0円です。")

st.caption(
    "回収率 = 払戻額 ÷ 購入額 × 100。"
    "回収率100%は収支±0円です。"
    "この機能は記録用であり、将来の利益を保証するものではありません。"
)


st.divider()
st.header("📈 STEP 18-3：通算収支ダッシュボード")

st.write(
    "保存した馬券収支CSVをまとめて読み込み、"
    "通算成績を集計します。"
)

st.caption(
    "STEP 18-2で保存した jra_bet_record.csv を使用できます。"
    "複数レースを集計する場合は、記録を1つのCSVにまとめてください。"
)

history_bet_file = st.file_uploader(
    "馬券収支の記録CSV",
    type=["csv"],
    key="history_bet_csv_uploader",
)

if history_bet_file is not None:
    try:
        try:
            history_bet_file.seek(0)
            bet_history = pd.read_csv(
                history_bet_file,
                encoding="utf-8-sig"
            )
        except UnicodeDecodeError:
            history_bet_file.seek(0)
            bet_history = pd.read_csv(
                history_bet_file,
                encoding="cp932"
            )

        bet_history.columns = (
            bet_history.columns.astype(str).str.strip()
        )

        required_bet_columns = [
            "レース名", "購入額", "払戻額"
        ]

        missing_bet_columns = [
            col for col in required_bet_columns
            if col not in bet_history.columns
        ]

        if missing_bet_columns:
            st.error(
                "CSVに必要な列がありません："
                + "、".join(missing_bet_columns)
            )
        else:
            bet_history["購入額"] = pd.to_numeric(
                bet_history["購入額"],
                errors="coerce"
            )

            bet_history["払戻額"] = pd.to_numeric(
                bet_history["払戻額"],
                errors="coerce"
            )

            valid = (
                bet_history["レース名"].notna()
                & (bet_history["レース名"].astype(str).str.strip() != "")
                & bet_history["購入額"].notna()
                & bet_history["払戻額"].notna()
                & (bet_history["購入額"] > 0)
                & (bet_history["払戻額"] >= 0)
            )

            invalid_count = int((~valid).sum())
            bet_history = bet_history.loc[valid].copy()

            if invalid_count:
                st.warning(
                    f"{invalid_count}行を無効なデータとして除外しました。"
                )

            if bet_history.empty:
                st.warning(
                    "集計できる有効な記録がありません。"
                )
            else:
                # CSV内の各行を1件の購入記録として集計
                bet_history["収支"] = (
                    bet_history["払戻額"]
                    - bet_history["購入額"]
                )

                total_bet = bet_history["購入額"].sum()
                total_payout = bet_history["払戻額"].sum()
                total_profit = total_payout - total_bet
                recovery_rate = (
                    total_payout / total_bet * 100
                )

                # レース単位の収支を集計
                race_summary = (
                    bet_history.groupby(
                        "レース名",
                        as_index=False
                    )
                    .agg(
                        購入額=("購入額", "sum"),
                        払戻額=("払戻額", "sum"),
                    )
                )

                race_summary["収支"] = (
                    race_summary["払戻額"]
                    - race_summary["購入額"]
                )

                win_races = int(
                    (race_summary["収支"] > 0).sum()
                )
                lose_races = int(
                    (race_summary["収支"] < 0).sum()
                )
                even_races = int(
                    (race_summary["収支"] == 0).sum()
                )

                st.subheader("通算成績")

                c1, c2 = st.columns(2)
                c1.metric(
                    "集計レース数",
                    f"{len(race_summary)}レース"
                )
                c2.metric(
                    "購入記録数",
                    f"{len(bet_history)}件"
                )

                c3, c4, c5 = st.columns(3)
                c3.metric(
                    "総購入額",
                    f"{total_bet:,.0f}円"
                )
                c4.metric(
                    "総払戻額",
                    f"{total_payout:,.0f}円"
                )
                c5.metric(
                    "通算収支",
                    f"{total_profit:+,.0f}円"
                )

                st.metric(
                    "通算回収率",
                    f"{recovery_rate:.1f}%"
                )

                c6, c7, c8 = st.columns(3)
                c6.metric("プラス収支", f"{win_races}レース")
                c7.metric("マイナス収支", f"{lose_races}レース")
                c8.metric("収支±0円", f"{even_races}レース")

                st.subheader("レース別収支")

                st.dataframe(
                    race_summary.sort_values(
                        "収支", ascending=False
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    label="📥 集計結果をCSV保存",
                    data=race_summary.to_csv(
                        index=False
                    ).encode("utf-8-sig"),
                    file_name="jra_bet_summary.csv",
                    mime="text/csv",
                    key="download_bet_summary",
                )

                st.caption(
                    "通算回収率 = 総払戻額 ÷ 総購入額 × 100。"
                    "同じレース名の記録は1レースとしてまとめます。"
                    "CSVの各行は購入記録として扱うため、"
                    "同じ記録を重複して取り込まないよう注意してください。"
                )

    except Exception as e:
        st.error(
            f"収支CSVの読み込みに失敗しました：{e}"
        )
