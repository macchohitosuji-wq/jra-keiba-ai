
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="複勝期待値AI",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 複勝期待値AI")
st.caption("JRA全レースから複勝の期待値が高い馬を厳選する開発版")

st.info("現在は手入力による期待値計算です。AIによる確率予測は今後追加します。")

st.subheader("① 出走馬データ")

default_data = pd.DataFrame([
    {"競馬場": "東京", "レース": "1R", "馬名": "テスト馬1", "3着内確率(%)": 60.0, "オッズ下限": 1.5, "オッズ上限": 2.0},
    {"競馬場": "東京", "レース": "1R", "馬名": "テスト馬2", "3着内確率(%)": 50.0, "オッズ下限": 2.0, "オッズ上限": 2.5},
    {"競馬場": "京都", "レース": "2R", "馬名": "テスト馬3", "3着内確率(%)": 40.0, "オッズ下限": 3.0, "オッズ上限": 4.0},
    {"競馬場": "福島", "レース": "3R", "馬名": "テスト馬4", "3着内確率(%)": 30.0, "オッズ下限": 4.0, "オッズ上限": 5.0},
    {"競馬場": "東京", "レース": "4R", "馬名": "テスト馬5", "3着内確率(%)": 20.0, "オッズ下限": 5.0, "オッズ上限": 8.0},
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

st.caption("行を追加して馬を増やせます。数値はテスト用なので自由に変更してください。")

st.subheader("② 期待値ランキング設定")

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
            venue = str(horse["競馬場"]).strip()
            race = str(horse["レース"]).strip()

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

            ev_low = p * low
            ev_mid = p * mid
            ev_high = p * high

            results.append({
                "競馬場": venue,
                "レース": race,
                "馬名": name,
                "3着内確率(%)": p * 100,
                "複勝下限": low,
                "複勝上限": high,
                "保守的期待値": ev_low,
                "中央値期待値": ev_mid,
                "上限期待値": ev_high,
                "判定": "候補" if ev_low > threshold else "見送り"
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

        st.subheader("③ 全馬ランキング")

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

        st.subheader("④ 厳選候補")

        col1, col2 = st.columns(2)

        col1.metric("分析した馬", len(df))
        col2.metric("買い候補", len(candidates))

        if len(candidates) > 0:
            st.success("保守的期待値の基準を満たした馬")
            st.dataframe(
                candidates,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("条件を満たす馬はいません。無理に購入する必要はありません。")

        csv = df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "ランキングをCSV保存",
            data=csv,
            file_name="place_ev_ranking.csv",
            mime="text/csv"
        )

        st.caption(
            "期待値＝3着内確率×複勝オッズ。"
            "この数値は入力した確率が正確であることを前提とした理論値です。"
        )

    else:
        st.warning("計算できる馬がありません。入力内容を確認してください。")
