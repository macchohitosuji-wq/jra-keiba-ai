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
