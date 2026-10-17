

import streamlit as st
import pandas as pd
from datetime import date
import json

st.set_page_config(
    page_title="JRA競馬予想AI",
    page_icon="🏇",
    layout="wide"
)


# 過去レースの記録を管理
if "race_history" not in st.session_state:
    try:
        with open(
            "race_history.json",
            "r",
            encoding="utf-8"
        ) as f:
            st.session_state["race_history"] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        st.session_state["race_history"] = []



st.title("🏇 JRA競馬予想AI")
st.write("全頭評価と買い目提案を目指す開発版です。")
st.info(
    "現在は手入力とCSV読み込みに対応しています。"
    "実際のJRAデータやAI予測とは連携していません。"
)

st.sidebar.header("レース設定")
race_date = st.sidebar.date_input(
    "開催日",
    value=date.today()
)

racecourse = st.sidebar.selectbox(
    "競馬場",
    ["東京", "中山", "京都", "阪神", "中京",
     "新潟", "福島", "小倉", "札幌", "函館"]
)

race_number = st.sidebar.selectbox(
    "レース番号",
    list(range(1, 13)),
    format_func=lambda x: f"{x}R"
)
st.sidebar.write("---")
st.sidebar.write("### 選択中のレース")
st.sidebar.write(f"開催日：{race_date.strftime('%Y年%m月%d日')}")
st.sidebar.write(f"競馬場：{racecourse}")
st.sidebar.write(f"レース：{race_number}R")
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
# ========================================
# 自動評価機能（無料・ルールベース）
# ========================================

def calculate_auto_score(row):
    """
    実際のデータをもとに評価点を計算するための土台。
    未評価の項目は勝手に高得点にしない。
    """
    score_columns = [
        "近走成績",
        "距離適性",
        "脚質・展開",
        "血統適性",
        "調教評価",
        "馬場適性",
    ]

    scores = []

    for col in score_columns:
        value = pd.to_numeric(
            row.get(col), errors="coerce"
        )

        if pd.notna(value):
            scores.append(float(value))

    if not scores:
        return None

    return round(sum(scores) / len(scores), 1)
columns = [
    "馬番", "馬名", "オッズ", "人気",
    "近走成績", "距離適性",
    "脚質・展開", "血統適性", "調教評価", "馬場適性"
]
st.subheader("📋 出馬表のコピペ取り込み")
import re

def parse_racecard(text):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    rows = []
    i = 0

    while i < len(lines):
        # 枠番＋馬番、または馬番だけの行を探す
        number_match = re.fullmatch(
            r"(?:(\d+)\s+)?(\d+)",
            lines[i]
        )

        if not number_match:
            i += 1
            continue

        horse_number = int(number_match.group(2))
        j = i + 1

        # 「--」を読み飛ばす
        if j < len(lines) and lines[j] == "--":
            j += 1

        # 馬名と詳細行がそろっているか確認
        if j + 1 >= len(lines):
            i += 1
            continue

        horse_name = lines[j]
        details = lines[j + 1].split()

        if (
            len(details) >= 7
            and re.fullmatch(r"(牡|牝|セ)\d+", details[0])
            and details[3].startswith(("美浦", "栗東"))
            and re.fullmatch(r"\d+\([+-]\d+\)", details[4])
        ):
            rows.append({
                "馬番": horse_number,
                "馬名": horse_name,
                "性齢": details[0],
                "斤量": float(details[1]),
                "騎手": details[2],
                "厩舎": details[3],
                "馬体重": details[4],
                "オッズ": float(details[5]),
                "人気": int(details[6]),
            })

            i = j + 2
        else:
            i += 1

    return pd.DataFrame(rows)
racecard_text = st.text_area(
    "出馬表をそのまま貼り付けてください",
    height=300,
    placeholder="ここに出馬表を貼り付け"
)

if st.button("出馬表を読み込む"):
    if racecard_text.strip():
        st.session_state["racecard_text"] = racecard_text
        st.success("出馬表を受け付けました。")

        parsed_racecard = parse_racecard(racecard_text)

        if not parsed_racecard.empty:
            st.subheader("🐎 取り込み結果")
            st.dataframe(
                parsed_racecard,
                use_container_width=True,
                hide_index=True
            )
            
                    # 照合結果を保存
                   
            st.success(
                f"{len(parsed_racecard)}頭のデータを取り込みました。"
            )
        else:
            st.warning(
                "馬データを読み取れませんでした。"
                "出馬表の形式を確認してください。"
            )
    else:
        st.warning("先に出馬表を貼り付けてください。")
sample = pd.DataFrame({
    "馬番": [1, 2, 3, 4, 5],
    "馬名": [
        "サンプルA", "サンプルB", "サンプルC",
        "サンプルD", "サンプルE"
    ],
    "オッズ": [3.2, 5.9, 8.4, 18.1, 29.0],
    "人気": [1, 2, 3, 4, 5],
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
# 出馬表テキストを予想AIの入力表に反映
# CSVがアップロードされている場合はCSVを優先する
if uploaded_file is None and st.session_state.get("racecard_text"):
    imported_horses = parse_racecard(
        st.session_state["racecard_text"]
    )

    if not imported_horses.empty:
        horses_input = imported_horses[
            ["馬番", "馬名", "オッズ", "人気"]
        ].copy()

        # 評価項目は仮の中立値
        for col in weights:
            horses_input[col] = 50

        horses_input = horses_input[columns]

        st.warning(
            "テキストから取り込んだ評価項目は仮の50点です。"
        )

        st.success(
            f"予想AIの入力表に{len(horses_input)}頭を反映しました。"
        )
st.download_button(
    label="📥 サンプルCSVをダウンロード",
    data=sample.to_csv(index=False).encode("utf-8-sig"),
    file_name="jra_horses_sample.csv",
    mime="text/csv"
)


st.divider()
st.subheader("🐎 実際の出走馬を取り込む")
st.write("JRA公式の出馬表からコピーした馬番・馬名を貼り付けてください。")

race_text = st.text_area(
    "出馬表のテキスト",
    placeholder="例：\n1\nサンプルホースA\n2\nサンプルホースB",
    height=180,
    key="race_text_input"
)

if st.button("馬番・馬名を取り込む"):
    import re

    lines = [
        line.strip()
        for line in race_text.splitlines()
        if line.strip()
    ]

    imported_horses = []
    i = 0

    while i < len(lines) - 1:
        if re.fullmatch(r"\d{1,2}", lines[i]):
            number = int(lines[i])
            name = lines[i + 1]

            if (
                1 <= number <= 18
                and not re.fullmatch(r"\d{1,2}", name)
                and len(name) <= 40
            ):
                imported_horses.append({
                    "馬番": number,
                    "馬名": name
                })
                i += 2
                continue

        i += 1

    if imported_horses:
        imported_df = pd.DataFrame(imported_horses)
        imported_df = imported_df.drop_duplicates(
            subset=["馬番"], keep="first"
        )

        st.session_state["imported_horses"] = imported_df
        st.success(
            f"{len(imported_df)}頭の馬番・馬名を取り込みました。"
        )
        st.dataframe(
            imported_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.error(
        "馬番・馬名を読み取れませんでした。"
        "馬番と馬名が別々の行になるように貼り付けてください。"
    )
# ========================================
# STEP 10：近走成績の入力と自動評価
# ========================================
st.subheader("📈 近走成績から自動評価")

st.write(
    "直近3走の確定着順を入力すると、"
    "近走成績の評価点を自動計算します。"
)

recent_results = st.data_editor(
    pd.DataFrame({
        "馬番": [1],
        "馬名": [""],
        "前走着順": [None],
        "2走前着順": [None],
        "3走前着順": [None],
    }),
    num_rows="dynamic",
    use_container_width=True,
    key="recent_results_editor",
    column_config={
        "馬番": st.column_config.NumberColumn(
            "馬番", min_value=1, step=1
        ),
        "馬名": st.column_config.TextColumn("馬名"),
        "前走着順": st.column_config.NumberColumn(
            "前走着順", min_value=1, step=1
        ),
        "2走前着順": st.column_config.NumberColumn(
            "2走前着順", min_value=1, step=1
        ),
        "3走前着順": st.column_config.NumberColumn(
            "3走前着順", min_value=1, step=1
        ),
    },
)

if not recent_results.empty:
    recent_cols = [
        "前走着順",
        "2走前着順",
        "3走前着順",
    ]

    for col in recent_cols:
        recent_results[col] = pd.to_numeric(
            recent_results[col], errors="coerce"
        )

    # 着順を点数化：1着100点、2着90点…10着以下10点
    def finish_to_score(position):
        if pd.isna(position) or position < 1:
            return None
        return max(10, 110 - int(position) * 10)

    recent_results["自動算出_近走成績"] = (
        recent_results[recent_cols]
        .map(finish_to_score)
        .mean(axis=1)
        .round(1)
    )

    st.dataframe(
        recent_results,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "暫定ルールによる点数です。未入力の走は平均から除外します。"
        "この点数は実証済みの予測モデルではありません。"
    )        


# ========================================
# 調教データのコピペ取り込み
# ========================================
st.divider()
st.subheader("🏋️ 調教評価・過去成績を取り込む")

st.caption(
    "調教評価の表をコピーして貼り付けてください。"
    "馬名・調教評価・着順別成績・回収率を読み取ります。"
)

training_text = st.text_area(
    "調教データ表",
    placeholder="調教データの表をコピーして貼り付け",
    height=250,
    key="training_text",
)


if st.button("調教データを読み取る"):
    import re

    # Markdownの表から1頭ずつデータを読み取る
    lines = [
        line.strip()
        for line in training_text.splitlines()
        if line.strip()
    ]
    st.write("調教データのコピー内容（確認用）")
    st.code(repr(training_text[:1500]))

    parsed_training = []

    for line in lines:
        if "|" not in line:
            continue

        # Markdown表の区切りを分割
        cells = [cell.strip() for cell in line.strip("|").split("|")]

        # 見出し・罫線は除外
        if len(cells) < 14:
            continue

        if all(
            re.fullmatch(r":?-+:?", re.sub(r"\s", "", cell))
            for cell in cells
        ):
            continue

        # Markdownの太字・リンクを除去
        cleaned = []

        for cell in cells:
            cell = re.sub(
                r"\[([^\]]+)\]\([^)]+\)",
                r"\1",
                cell
            )
            cell = cell.replace("**", "").strip()
            cleaned.append(cell)

        # 馬番、馬名、調教評価を抽出
        try:
            number = int(cleaned[0])
        except (ValueError, IndexError):
            continue

        name = cleaned[2]

        rating_match = re.search(
            r"調教:([ABC])",
            cleaned[3]
        )

        if not rating_match:
            continue

        # 1着・2着・3着・4着以下・出走回数
        try:
            results = [
                int(cleaned[i].replace(",", ""))
                for i in range(4, 9)
            ]

            percentages = [
                float(cleaned[i].replace("%", "").replace(",", ""))
                for i in range(9, 14)
            ]
        except (ValueError, IndexError):
            continue

        parsed_training.append({
            "馬番": number,
            "馬名": name,
            "調教評価": rating_match.group(1),
            "1着": results[0],
            "2着": results[1],
            "3着": results[2],
            "4着以下": results[3],
            "出走回数": results[4],
            "勝率(%)": percentages[0],
            "連対率(%)": percentages[1],
            "複勝率(%)": percentages[2],
            "単勝回収率(%)": percentages[3],
            "複勝回収率(%)": percentages[4],
        })

    if parsed_training:
        training_df = pd.DataFrame(parsed_training)

        training_df = training_df.drop_duplicates(
            subset=["馬番"],
            keep="first"
        )

        st.success(
            f"{len(training_df)}頭分の調教データを読み取りました。"
        )

        st.dataframe(
            training_df,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "読み取り結果の確認用です。"
            "まだ予想AIの評価には反映していません。"
        )
    else:
        st.error(
            "データを読み取れませんでした。"
            "表全体をコピーして貼り付けてください。"
        )

st.header("📋 出走馬データ")

# ========================================
# タイム指数データのコピペ取り込み
# ========================================
st.divider()
st.subheader("📊 タイム指数をコピペで取り込む")

st.caption(
    "JRA・競馬情報サイトのタイム指数表をコピーして貼り付けてください。"
    "馬番・馬名・指数・オッズ・人気を自動で読み取ります。"
)

time_index_text = st.text_area(
    "タイム指数表",
    placeholder="表の見出しから最終馬までコピーして貼り付け",
    height=250,
    key="time_index_text",
)




if st.button("タイム指数を読み取る"):
    import re

    lines = [
        line.strip()
        for line in time_index_text.splitlines()
        if line.strip()
    ]

    parsed_horses = []
    i = 0

    while i < len(lines):
        # 枠番 → 馬番 → 印 → 馬名とデータ
        if (
            re.fullmatch(r"\d{1,2}\t?", lines[i])
            and i + 3 < len(lines)
            and re.fullmatch(r"\d{1,2}", lines[i + 1])
            and re.fullmatch(r"--?", lines[i + 2])
        ):
            frame = int(lines[i].replace("\t", ""))
            number = int(lines[i + 1])

            # 馬名・性齢・斤量・騎手・指数などはタブ区切り
            parts = [
                part.strip()
                for part in lines[i + 3].split("\t")
                if part.strip()
            ]

            if len(parts) >= 13:
                name = parts[0]

                # 性齢・斤量・騎手の後ろにある9項目
                try:
                    nums = [
                        float(value.replace("*", ""))
                        for value in parts[-9:]
                    ]

                    parsed_horses.append({
                        "枠番": frame,
                        "馬番": number,
                        "馬名": name,
                        "最高": nums[0],
                        "5走平均": nums[1],
                        "距離": nums[2],
                        "コース": nums[3],
                        "3走前": nums[4],
                        "2走前": nums[5],
                        "前走": nums[6],
                        "単勝オッズ": nums[7],
                        "人気": int(nums[8]),
                    })
                except (ValueError, IndexError):
                    pass

            i += 4
        else:
            i += 1

    if parsed_horses:
        parsed_df = pd.DataFrame(parsed_horses)

        st.success(
            f"{len(parsed_df)}頭分のデータを読み取りました。"
        )

        st.dataframe(
            parsed_df,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "この段階では確認用です。予想AIへの反映はまだ行いません。"
        )
    else:
        st.error(
            "読み取りに失敗しました。"
            "入力データと解析形式をもう一度確認しましょう。"
        )



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

    horses["馬名"] = (
        horses["馬名"].fillna("").astype(str).str.strip()
    )

    for col in weights:
        horses[col] = pd.to_numeric(
            horses[col], errors="coerce"
        )

    # 6項目すべてが50点なら評価未確認とする
    score_columns = list(weights.keys())

    horses["評価未確認"] = (
        horses[score_columns].eq(50).all(axis=1)
    )

    # 配点に基づく総合評価点
    horses["評価点"] = sum(
        horses[col] * weight
        for col, weight in weights.items()
    ).round(1)

    horses = horses.dropna(
        subset=["評価点", "馬番"]
    )

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
    # 評価未確認の馬がいる場合は警告
if "評価未確認" in horses.columns:
    unconfirmed = horses[horses["評価未確認"]]

    if not unconfirmed.empty:
        st.warning(
            f"評価が未確認の馬が{len(unconfirmed)}頭います。"
            "全項目50点のため、実際の適性を評価できていません。"
        )

        st.dataframe(
            unconfirmed[["馬番", "馬名"]],
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
                    
                    # 照合結果を保存
                    if st.button("💾 このレースの結果を保存"):
                        race_key = (
                            f"{race_date}_{racecourse}_{race_number}"
                        )

                        already_saved = any(
                            row["レースID"] == race_key
                            for row in st.session_state["race_history"]
                        )

                        if already_saved:
                            st.warning("このレースはすでに保存されています。")
                        else:
                            for _, row in comparison.iterrows():
                                st.session_state["race_history"].append({
                                    "レースID": race_key,
                                    "開催日": str(race_date),
                                    "競馬場": racecourse,
                                    "レース番号": f"{race_number}R",
                                    "馬番": int(row["馬番"]),
                                    "馬名": row["馬名"],
                                    "評価点": float(row["評価点"]),
                                    "印": row["印"],
                                    "着順": int(row["着順"]),
                                })

                            try:
                                with open(
                                    "race_history.json",
                                    "w",
                                    encoding="utf-8"
                                ) as f:
                                    json.dump(
                                        st.session_state["race_history"],
                                        f,
                                        ensure_ascii=False,
                                        indent=2
                                    )

                                st.success(
                                    f"{len(comparison)}頭分の結果を保存しました！"
                                )

                            except Exception as e:
                                st.error(f"ファイル保存に失敗しました：{e}")


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


st.divider()
st.header("🔍 STEP 19：予想印ごとの成績分析")

st.write(
    "過去の検証記録から、予想印ごとの成績を集計します。"
)

analysis_file = st.file_uploader(
    "予想と確定着順の検証記録CSV",
    type=["csv"],
    key="mark_analysis_csv_uploader",
)

if analysis_file is not None:
    try:
        try:
            analysis_file.seek(0)
            analysis_df = pd.read_csv(
                analysis_file, encoding="utf-8-sig"
            )
        except UnicodeDecodeError:
            analysis_file.seek(0)
            analysis_df = pd.read_csv(
                analysis_file, encoding="cp932"
            )

        analysis_df.columns = (
            analysis_df.columns.astype(str).str.strip()
        )

        required_columns = [
            "レース名", "馬番", "馬名", "評価点", "印", "着順"
        ]

        missing_columns = [
            col for col in required_columns
            if col not in analysis_df.columns
        ]

        if missing_columns:
            st.error(
                "CSVに必要な列がありません："
                + "、".join(missing_columns)
            )
        else:
            analysis_df["着順"] = pd.to_numeric(
                analysis_df["着順"], errors="coerce"
            )
            analysis_df["評価点"] = pd.to_numeric(
                analysis_df["評価点"], errors="coerce"
            )
            analysis_df["印"] = (
                analysis_df["印"].fillna("").astype(str).str.strip()
            )

            analysis_df = analysis_df.dropna(
                subset=["着順", "評価点"]
            )
            analysis_df = analysis_df[
                analysis_df["着順"] >= 1
            ].copy()

            if analysis_df.empty:
                st.warning("分析できる着順データがありません。")
            else:
                analysis_df["3着以内"] = (
                    analysis_df["着順"] <= 3
                )

                st.subheader("印ごとの成績")

                mark_order = ["◎", "○", "▲", "△", "☆"]
                mark_data = analysis_df[
                    analysis_df["印"].isin(mark_order)
                ].copy()

                if mark_data.empty:
                    st.info("分析対象の予想印がありません。")
                else:                        
                    mark_summary = mark_data.groupby("印").agg({
                        "着順": ["count", "mean"],
                        "3着以内": "sum",
                        "評価点": "mean",
                    })

                    mark_summary.columns = [
                        "頭数",
                        "平均着順",
                        "3着以内頭数",
                        "平均評価点",
                    ]

                    mark_summary = (
                        mark_summary
                        .reindex(mark_order)
                        .dropna(subset=["頭数"])
                        .reset_index()
                    )


                    mark_summary["3着以内率(%)"] = (
                        mark_summary["3着以内頭数"]
                        / mark_summary["頭数"] * 100
                    ).round(1)

                    mark_summary["平均着順"] = (
                        mark_summary["平均着順"].round(2)
                    )
                    mark_summary["平均評価点"] = (
                        mark_summary["平均評価点"].round(1)
                    )

                    st.dataframe(
                        mark_summary,
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.bar_chart(
                        mark_summary.set_index("印")["3着以内率(%)"]
                    )

                st.subheader("評価点と着順の関係")

                correlation_data = analysis_df[
                    ["評価点", "着順"]
                ].dropna()

                if (
                    len(correlation_data) >= 2
                    and correlation_data["評価点"].nunique() > 1
                    and correlation_data["着順"].nunique() > 1
                ):
                    
                    score_ranks = correlation_data["評価点"].rank(
                        method="average", ascending=False
                    )
                    finish_ranks = correlation_data["着順"].rank(
                        method="average", ascending=True
                    )

                    correlation = score_ranks.corr(finish_ranks)


                    st.metric(
                        "評価点と着順の順位相関",
                        f"{correlation:.3f}"
                    )
                    st.caption(
                        "負の値が強いほど、高評価の馬ほど"
                        "上位に入る傾向を示します。"
                        "少数レースでは数値が安定しません。"
                    )
                else:
                    st.info(
                        "相関の計算には、評価点と着順に"
                        "ばらつきのある複数頭の記録が必要です。"
                    )

                st.subheader("読み込んだ記録")
                st.dataframe(
                    analysis_df[required_columns],
                    use_container_width=True,
                    hide_index=True,
                )

                st.caption(
                    "過去データの集計であり、将来の的中を"
                    "保証するものではありません。"
                    "取消・競走中止などは別途扱う必要があります。"
                )

    except Exception as e:
        st.error(f"検証記録の分析に失敗しました：{e}")
        
# ========================================
# 過去レースの記録一覧
# ========================================

st.header("📚 過去レースの記録")

history = st.session_state["race_history"]

if history:
    history_df = pd.DataFrame(history)

    # 数値データを集計できる形に整える
    history_df["着順"] = pd.to_numeric(
        history_df["着順"], errors="coerce"
    )
    history_df["評価点"] = pd.to_numeric(
        history_df["評価点"], errors="coerce"
    )

    # レース単位で集計
    race_count = history_df["レースID"].nunique()

    honmei_df = history_df[
        history_df["印"] == "◎"
    ].dropna(subset=["着順"])

    if not honmei_df.empty:
        honmei_win_rate = (
            (honmei_df["着順"] == 1).mean() * 100
        )
        honmei_place_rate = (
            (honmei_df["着順"] <= 3).mean() * 100
        )
    else:
        honmei_win_rate = 0.0
        honmei_place_rate = 0.0

    # 各レースの評価上位3頭を抽出
    top3_list = []

    for race_id, group in history_df.groupby("レースID"):
        group = group.dropna(
            subset=["評価点", "着順"]
        )

        top3 = group.sort_values(
            "評価点", ascending=False
        ).head(3)

        if not top3.empty:
            top3_list.append(top3)

    if top3_list:
        top3_df = pd.concat(
            top3_list, ignore_index=True
        )
        top3_place_rate = (
            (top3_df["着順"] <= 3).mean() * 100
        )
        top3_hit_count = int(
            (top3_df["着順"] <= 3).sum()
        )
        top3_total = len(top3_df)
    else:
        top3_place_rate = 0.0
        top3_hit_count = 0
        top3_total = 0

    # 集計ダッシュボード
    st.subheader("📈 予想精度ダッシュボード")

    col1, col2 = st.columns(2)
    col1.metric("記録レース数", f"{race_count}レース")
    col2.metric("◎の勝率", f"{honmei_win_rate:.1f}%")

    col3, col4 = st.columns(2)
    col3.metric("◎の複勝率", f"{honmei_place_rate:.1f}%")
    col4.metric(
        "評価上位3頭の複勝圏入り率",
        f"{top3_place_rate:.1f}%"
    )

    st.caption(
        f"◎の集計対象：{len(honmei_df)}頭分"
        f" ／ 評価上位3頭：{top3_hit_count}/{top3_total}頭"
    )

    st.divider()

    # 記録一覧
    st.subheader("📋 保存したレース結果")

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
    )

    # CSVでダウンロード
    st.download_button(
        label="📥 過去レースの記録をCSV保存",
        data=history_df.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name="jra_race_history.csv",
        mime="text/csv",
    )

else:
    st.info(
        "まだ記録がありません。"
        "予想と結果を照合し、保存ボタンを押してください。"
    )

# ========================================
# STEP 18：過去レースデータの取り込み
# ========================================
st.header("📚 STEP 18：過去レースデータの分析")

st.write(
    "過去レースの各評価項目と確定着順を読み込み、"
    "予想基準を検証するためのデータを作成します。"
)

historical_columns = [
    "レースID",
    "馬番",
    "馬名",
    "近走成績",
    "距離適性",
    "脚質・展開",
    "血統適性",
    "調教評価",
    "馬場適性",
    "着順",
]

historical_sample = pd.DataFrame({
    "レースID": [
        "2026_sample_01",
        "2026_sample_01",
        "2026_sample_01",
        "2026_sample_01",
        "2026_sample_01",
    ],
    "馬番": [1, 2, 3, 4, 5],
    "馬名": [
        "サンプルA",
        "サンプルB",
        "サンプルC",
        "サンプルD",
        "サンプルE",
    ],
    "近走成績": [90, 80, 75, 65, 60],
    "距離適性": [85, 80, 90, 70, 65],
    "脚質・展開": [80, 85, 75, 70, 60],
    "血統適性": [80, 75, 85, 70, 65],
    "調教評価": [85, 80, 75, 70, 60],
    "馬場適性": [80, 85, 75, 70, 65],
    "着順": [1, 3, 2, 4, 5],
})

st.download_button(
    label="📥 過去レースCSVのサンプルをダウンロード",
    data=historical_sample.to_csv(
        index=False
    ).encode("utf-8-sig"),
    file_name="historical_race_sample.csv",
    mime="text/csv",
)

historical_file = st.file_uploader(
    "過去レースデータCSVをアップロード",
    type=["csv"],
    key="historical_race_uploader",
)

if historical_file is not None:
    try:
        try:
            historical_file.seek(0)
            historical_df = pd.read_csv(
                historical_file,
                encoding="utf-8-sig"
            )
        except UnicodeDecodeError:
            historical_file.seek(0)
            historical_df = pd.read_csv(
                historical_file,
                encoding="cp932"
            )

        historical_df.columns = (
            historical_df.columns.astype(str).str.strip()
        )

        missing_columns = [
            col for col in historical_columns
            if col not in historical_df.columns
        ]

        if missing_columns:
            st.error(
                "不足している列："
                + "、".join(missing_columns)
            )
            st.caption(
                "サンプルCSVをダウンロードし、"
                "列名を合わせてください。"
            )
        else:
            historical_df = historical_df[
                historical_columns
            ].copy()

            numeric_columns = [
                "馬番",
                "近走成績",
                "距離適性",
                "脚質・展開",
                "血統適性",
                "調教評価",
                "馬場適性",
                "着順",
            ]

            for col in numeric_columns:
                historical_df[col] = pd.to_numeric(
                    historical_df[col],
                    errors="coerce"
                )

            if historical_df[numeric_columns].isna().any().any():
                st.error(
                    "数値の列に空欄や数値以外のデータがあります。"
                    "CSVを確認してください。"
                )
            elif (
                (historical_df["着順"] < 1).any()
                or (historical_df["馬番"] < 1).any()
            ):
                st.error(
                    "馬番と着順は1以上の数値にしてください。"
                )
            elif (
                historical_df["レースID"].isna().any()
                or historical_df["レースID"].astype(str).str.strip().eq("").any()
            ):
                st.error("レースIDに空欄があります。")
            elif historical_df.duplicated(
                subset=["レースID", "馬番"]
            ).any():
                st.error(
                    "同じレースIDに重複した馬番があります。"
                )
            else:
                st.success(
                    f"{len(historical_df)}頭分のデータを読み込みました。"
                )

                st.metric(
                    "読み込んだレース数",
                    f"{historical_df['レースID'].nunique()}レース"
                )

                st.dataframe(
                    historical_df,
                    use_container_width=True,
                    hide_index=True,
                )
                
                st.subheader("📊 評価項目と確定着順の関係")

                score_columns = [
                    "近走成績",
                    "距離適性",
                    "脚質・展開",
                    "血統適性",
                    "調教評価",
                    "馬場適性",
                ]

                if (
                    historical_df["レースID"].nunique() < 2
                    or len(historical_df) < 5
                ):
                    st.info(
                        "分析には複数レースのデータを推奨します。"
                        "現在は参考値として確認してください。"
                    )

                correlations = (
                    historical_df[
                        score_columns + ["着順"]
                    ]
                    .corr(method="spearman")["着順"]
                    .drop("着順")
                    .rename("着順との相関")
                    .reset_index()
                    .rename(columns={"index": "評価項目"})
                )

                correlations["着順との相関"] = (
                    correlations["着順との相関"].round(3)
                )

                st.dataframe(
                    correlations,
                    use_container_width=True,
                    hide_index=True,
                )

                st.caption(
                    "相関がマイナスなら、その評価項目が高い馬ほど"
                    "着順の数字が小さい傾向、プラスなら逆の傾向です。"
                    "相関は因果関係を示すものではなく、"
                    "データが少ない場合は結果が不安定です。"
                )


    except Exception as e:
        st.error(
            f"CSVの読み込みに失敗しました：{e}"
        )
