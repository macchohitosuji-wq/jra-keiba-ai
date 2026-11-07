import streamlit as st
import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

st.set_page_config(page_title="複勝期待値AI", page_icon="🏇", layout="wide")
st.title("🏇 複勝期待値AI")
st.caption("TARGETの過去成績から3着以内確率を試算し、複勝オッズと組み合わせて期待値を確認する試作版")

st.warning(
    "試作モデルです。収録データは今回出走馬を中心とした過去成績で、全JRA全馬の網羅データではありません。"
    "表示確率・期待値は購入を保証するものではなく、まずは今日のレースで動作と予測傾向を確認する目的で使ってください。"
)

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

FEATURES = [
    "過去出走数", "直近5走3着内率", "通算3着内率",
    "直近5走平均着順", "直近3走平均着順",
    "同競馬場3着内率", "同距離帯3着内率", "同距離帯出走数",
    "前走からの日数", "前走着順", "今回距離", "今回年齢",
    "今回斤量", "今回頭数"
]


def read_target_csv(uploaded_file):
    uploaded_file.seek(0)
    try:
        return pd.read_csv(uploaded_file, header=None, dtype=str, encoding="cp932")
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, header=None, dtype=str, encoding="utf-8-sig")


def clean_id(value):
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def parse_entry_date(value):
    """TARGET出馬表の日付を可能な範囲で日付に変換する。"""
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 8:
        return pd.to_datetime(digits, format="%Y%m%d", errors="coerce")
    if len(digits) == 6:
        return pd.to_datetime("20" + digits, format="%Y%m%d", errors="coerce")
    return pd.to_datetime(text, errors="coerce")


def prepare_history(uploaded_file):
    raw = read_target_csv(uploaded_file)
    if raw.shape[1] != 52:
        raise ValueError(
            f"過去成績CSVは52列のフルセット形式が必要です。読み込み列数は{raw.shape[1]}列でした。"
        )
    data = raw.copy()
    data.columns = HISTORY_COLUMNS

    numeric_cols = [
        "年", "月", "日", "距離", "年齢", "斤量", "頭数", "確定着順",
        "異常コード", "補正タイム", "上がり3Fタイム", "人気順", "馬体重"
    ]
    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col].astype(str).str.strip(), errors="coerce")

    data["開催日"] = pd.to_datetime(
        {
            "year": 2000 + data["年"],
            "month": data["月"],
            "day": data["日"]
        },
        errors="coerce"
    )
    data["馬ID"] = data["血統登録番号"].map(clean_id)
    data["馬名キー"] = data["馬名"].fillna("").astype(str).str.strip()
    data["3着内実績"] = (
        data["確定着順"].between(1, 3) & (data["異常コード"] == 0)
    ).astype(int)

    valid = data[
        data["開催日"].notna()
        & data["確定着順"].between(1, 18)
        & (data["異常コード"] == 0)
        & (data["馬ID"] != "")
    ].copy()

    if valid.empty:
        raise ValueError("有効な着順データがありません。CSVの列形式を確認してください。")
    return data, valid


def features_from_prior(prior, current):
    """現在のレースより前の戦歴だけから特徴量を作る。"""
    prior = prior.sort_values(["開催日", "レースID"])
    last5 = prior.tail(5)
    last3 = prior.tail(3)
    venue_rows = prior[prior["競馬場"].astype(str).str.strip() == str(current.get("競馬場", "")).strip()]
    distance = pd.to_numeric(pd.Series([current.get("距離")]), errors="coerce").iloc[0]
    if pd.notna(distance):
        distance_rows = prior[(prior["距離"] - distance).abs() <= 200]
    else:
        distance_rows = prior.iloc[0:0]

    latest = prior.iloc[-1]
    current_age = pd.to_numeric(pd.Series([current.get("年齢")]), errors="coerce").iloc[0]
    current_weight = pd.to_numeric(pd.Series([current.get("斤量")]), errors="coerce").iloc[0]
    current_field = pd.to_numeric(pd.Series([current.get("頭数")]), errors="coerce").iloc[0]

    return {
        "過去出走数": len(prior),
        "直近5走3着内率": last5["3着内実績"].mean(),
        "通算3着内率": prior["3着内実績"].mean(),
        "直近5走平均着順": last5["確定着順"].mean(),
        "直近3走平均着順": last3["確定着順"].mean(),
        "同競馬場3着内率": venue_rows["3着内実績"].mean() if len(venue_rows) else np.nan,
        "同距離帯3着内率": distance_rows["3着内実績"].mean() if len(distance_rows) else np.nan,
        "同距離帯出走数": len(distance_rows),
        "前走からの日数": (pd.Timestamp(current["開催日"]) - pd.Timestamp(latest["開催日"])).days,
        "前走着順": latest["確定着順"],
        "今回距離": distance if pd.notna(distance) else np.nan,
        "今回年齢": current_age,
        "今回斤量": current_weight,
        "今回頭数": current_field
    }


def make_training_frame(valid):
    rows = []
    # 各馬の各レースについて、そのレース当日より前の戦歴だけを特徴量に使う
    for horse_id, group in valid.groupby("馬ID", sort=False):
        group = group.sort_values(["開催日", "レースID"])
        for _, current in group.iterrows():
            prior = group[group["開催日"] < current["開催日"]]
            if prior.empty:
                continue
            row = features_from_prior(prior, current)
            row["開催日"] = current["開催日"]
            row["正解"] = int(current["3着内実績"])
            rows.append(row)
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("過去走が1走以上ある学習対象馬がありません。")
    return result


def fit_model(training):
    training = training.sort_values("開催日").reset_index(drop=True)
    unique_dates = np.sort(training["開催日"].dropna().unique())
    if len(unique_dates) >= 5:
        split_index = max(1, int(len(unique_dates) * 0.8))
        split_date = pd.Timestamp(unique_dates[split_index])
        train_part = training[training["開催日"] < split_date]
        test_part = training[training["開催日"] >= split_date]
    else:
        split_date = None
        train_part = training.iloc[0:0]
        test_part = training.iloc[0:0]

    evaluation = None
    if len(train_part) >= 100 and len(test_part) >= 50 and test_part["正解"].nunique() == 2:
        validation_model = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(C=0.5, max_iter=1000, random_state=42)
        )
        validation_model.fit(train_part[FEATURES], train_part["正解"])
        test_prob = validation_model.predict_proba(test_part[FEATURES])[:, 1]
        evaluation = {
            "検証期間": f"{test_part['開催日'].min():%Y/%m/%d}〜{test_part['開催日'].max():%Y/%m/%d}",
            "検証件数": len(test_part),
            "Brierスコア": brier_score_loss(test_part["正解"], test_prob),
            "平均確率の基準Brier": brier_score_loss(
                test_part["正解"],
                np.full(len(test_part), train_part["正解"].mean())
            ),
            "AUC": roc_auc_score(test_part["正解"], test_prob)
        }

    final_model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(C=0.5, max_iter=1000, random_state=42)
    )
    final_model.fit(training[FEATURES], training["正解"])
    return final_model, evaluation


def prepare_entries(uploaded_file):
    raw = read_target_csv(uploaded_file)
    if raw.shape[1] < 22:
        raise ValueError(f"出馬表CSVの列数が不足しています（{raw.shape[1]}列）。")
    entries = pd.DataFrame({
        "開催日_raw": raw.iloc[:, 0].astype(str).str.strip(),
        "競馬場": raw.iloc[:, 1].astype(str).str.strip(),
        "レース": raw.iloc[:, 2].astype(str).str.strip().str.replace("R", "", regex=False) + "R",
        "馬番": raw.iloc[:, 3].astype(str).str.strip(),
        "クラス": raw.iloc[:, 4].astype(str).str.strip(),
        "コース": raw.iloc[:, 5].astype(str).str.strip(),
        "距離": pd.to_numeric(raw.iloc[:, 6].astype(str).str.strip(), errors="coerce"),
        "馬名": raw.iloc[:, 7].astype(str).str.strip(),
        "性別": raw.iloc[:, 8].astype(str).str.strip(),
        "年齢": pd.to_numeric(raw.iloc[:, 9].astype(str).str.strip(), errors="coerce"),
        "騎手": raw.iloc[:, 10].astype(str).str.strip(),
        "斤量": pd.to_numeric(raw.iloc[:, 11].astype(str).str.strip(), errors="coerce"),
        "調教師": raw.iloc[:, 12].astype(str).str.strip(),
        "父": raw.iloc[:, 16].astype(str).str.strip(),
        "母": raw.iloc[:, 17].astype(str).str.strip(),
        "馬ID": raw.iloc[:, 18].map(clean_id),
        "母父": raw.iloc[:, 20].astype(str).str.strip()
    })
    entries["開催日"] = entries["開催日_raw"].map(parse_entry_date)
    entries = entries[entries["馬名"].ne("")].copy()
    entries["頭数"] = entries.groupby(["競馬場", "レース"])["馬名"].transform("count")
    return entries



VENUE_CODE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉"
}

def prepare_place_odds(uploaded_file):
    """TARGETの複勝オッズCSV（レースID＋馬番別Lo/Hi）を縦形式に変換する。"""
    uploaded_file.seek(0)
    try:
        raw = pd.read_csv(uploaded_file, dtype=str, encoding="cp932")
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        raw = pd.read_csv(uploaded_file, dtype=str, encoding="utf-8-sig")

    raw.columns = [str(c).strip() for c in raw.columns]
    if "レースID" not in raw.columns:
        raise ValueError("CSVに『レースID』列がありません。TARGETの複勝オッズCSVを選択してください。")

    rows = []
    for _, row in raw.iterrows():
        race_id = clean_id(row.get("レースID", ""))
        if len(race_id) < 16 or not race_id[:8].isdigit():
            continue
        date = pd.to_datetime(race_id[:8], format="%Y%m%d", errors="coerce")
        venue_code = race_id[8:10]
        venue = VENUE_CODE_MAP.get(venue_code)
        race_no = str(int(race_id[-2:])) if race_id[-2:].isdigit() else ""
        if pd.isna(date) or venue is None or not race_no:
            continue

        for horse_no in range(1, 19):
            low_col, high_col = f"{horse_no}-Lo", f"{horse_no}-Hi"
            if low_col not in raw.columns or high_col not in raw.columns:
                continue
            low = pd.to_numeric(row.get(low_col), errors="coerce")
            high = pd.to_numeric(row.get(high_col), errors="coerce")
            if pd.notna(low) and pd.notna(high) and low >= 1 and high >= low:
                rows.append({
                    "開催日": date, "競馬場": venue, "レース番号_key": race_no,
                    "馬番_key": str(horse_no),
                    "複勝オッズ下限": float(low), "複勝オッズ上限": float(high)
                })

    odds = pd.DataFrame(rows)
    if odds.empty:
        raise ValueError("有効な複勝オッズが見つかりません。Lo/Hi列とレースIDを確認してください。")
    return odds.drop_duplicates(
        ["開催日", "競馬場", "レース番号_key", "馬番_key"], keep="last"
    )


def attach_place_odds(predictions, odds):
    """開催日・競馬場・レース番号・馬番で複勝オッズを照合する。"""
    result = predictions.copy()
    result["レース番号_key"] = result["レース"].astype(str).str.extract(r"(\d+)", expand=False)
    result["馬番_key"] = result["馬番"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    result["開催日"] = pd.to_datetime(result["開催日"], errors="coerce")
    result = result.merge(
        odds, on=["開催日", "競馬場", "レース番号_key", "馬番_key"], how="left", validate="many_to_one"
    )
    return result.drop(columns=["レース番号_key", "馬番_key"])

def predict_entries(entries, valid, model):
    predictions = []
    history_by_id = {k: g.sort_values(["開催日", "レースID"]) for k, g in valid.groupby("馬ID")}
    history_by_name = {
        k: g.sort_values(["開催日", "レースID"])
        for k, g in valid[valid["馬名キー"].ne("")].groupby("馬名キー")
    }

    for _, entry in entries.iterrows():
        hid = clean_id(entry["馬ID"])
        name = str(entry["馬名"]).strip()
        horse_history = history_by_id.get(hid) if hid else None
        match_method = "血統登録番号"
        if horse_history is None or horse_history.empty:
            possible = history_by_name.get(name)
            if possible is not None and not possible.empty and possible["馬ID"].nunique() == 1:
                horse_history = possible
                match_method = "馬名（補助照合）"
            else:
                horse_history = None

        race_date = entry["開催日"]
        if pd.isna(race_date):
            race_date = valid["開催日"].max() + pd.Timedelta(days=1)
        if horse_history is not None:
            prior = horse_history[horse_history["開催日"] < race_date]
        else:
            prior = None

        probability = np.nan
        status = "判定保留"
        if prior is not None and not prior.empty:
            current = entry.to_dict()
            current["開催日"] = race_date
            feats = features_from_prior(prior, current)
            x = pd.DataFrame([feats], columns=FEATURES)
            probability = float(model.predict_proba(x)[0, 1])
            status = "予測あり"
        predictions.append({
            "開催日": race_date,
            "競馬場": entry["競馬場"],
            "レース": entry["レース"],
            "馬番": entry["馬番"],
            "馬名": name,
            "騎手": entry["騎手"],
            "AI3着内確率(%)": round(probability * 100, 1) if pd.notna(probability) else np.nan,
            "照合方法": match_method if status == "予測あり" else "履歴なし",
            "AI判定": status
        })
    return pd.DataFrame(predictions)


# -------------------- ① 過去成績 --------------------
st.subheader("① TARGET過去成績CSV（フルセット＋単オッズ）")
history_file = st.file_uploader(
    "全馬成績CSVを選択（例：DS261107.CSV）",
    type=["csv"],
    key="history_csv"
)

valid_data = None
model = None
training_frame = None

if history_file is not None:
    try:
        all_history, valid_data = prepare_history(history_file)
        training_frame = make_training_frame(valid_data)
        model, evaluation = fit_model(training_frame)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("読み込み行数", f"{len(all_history):,}")
        c2.metric("収録馬数", f"{valid_data['馬ID'].nunique():,}")
        c3.metric("学習可能な過去走", f"{len(training_frame):,}")
        c4.metric("3着内実績", f"{int(valid_data['3着内実績'].sum()):,}")
        st.success("過去成績を読み込み、試作モデルを学習しました。")

        if evaluation:
            st.markdown("**時系列で分けた簡易検証（未来側20%）**")
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("検証件数", f"{evaluation['検証件数']:,}")
            e2.metric("モデルBrier", f"{evaluation['Brierスコア']:.3f}")
            e3.metric("平均確率Brier", f"{evaluation['平均確率の基準Brier']:.3f}")
            e4.metric("AUC", f"{evaluation['AUC']:.3f}")
            st.caption(
                f"検証期間：{evaluation['検証期間']}。Brierは低いほど良く、AUCは0.5がランダム相当です。"
                "平均確率BrierよりモデルBrierが低いかも確認してください。"
                "この検証は同じ収録馬群の時系列テストであり、全JRAへの汎化性能や回収率を保証しません。"
            )
        else:
            st.info("検証に必要な期間・件数が不足しているため、精度指標は表示していません。")

        with st.expander("学習に使った特徴量"):
            st.write("過去出走数、直近5走の3着内率、通算3着内率、直近の着順、同競馬場・同距離帯の成績、前走からの日数、今回の距離・年齢・斤量・頭数。")
            st.caption("各過去レースの予測特徴量は、そのレース当日より前の戦歴だけから作成しています。")
    except Exception as e:
        st.error(f"過去成績CSVの処理でエラーが発生しました：{e}")
        valid_data = None
        model = None

st.divider()

# -------------------- ② 当日出馬表 --------------------
st.subheader("② TARGET出馬表CSV")
entries_file = st.file_uploader(
    "今日の出馬表CSVを選択（例：DE261107.CSV）",
    type=["csv"],
    key="entries_csv"
)

if entries_file is not None:
    try:
        entries = prepare_entries(entries_file)
        race_summary = (
            entries.groupby(["競馬場", "レース"], sort=False)
            .agg(出走頭数=("馬名", "count"), 距離=("距離", "first"), コース=("コース", "first"))
            .reset_index()
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("競馬場数", entries["競馬場"].nunique())
        c2.metric("レース数", len(race_summary))
        c3.metric("出走馬数", len(entries))
        st.dataframe(race_summary, use_container_width=True, hide_index=True)

        if model is None or valid_data is None:
            st.warning("先に①へ過去成績CSVをアップロードしてください。")
        else:
            predictions = predict_entries(entries, valid_data, model)
            st.subheader("③ AIの3着以内確率")
            st.caption("血統登録番号で照合します。番号が一致しない場合は馬名で補助照合し、履歴がない馬は判定保留です。")
            st.dataframe(
                predictions[["競馬場", "レース", "馬番", "馬名", "騎手", "AI3着内確率(%)", "照合方法", "AI判定"]],
                use_container_width=True,
                hide_index=True
            )

            st.subheader("④ TARGET複勝オッズCSVを読み込む")
            odds_file = st.file_uploader(
                "複勝オッズCSVを選択（例：261107huku.csv）",
                type=["csv"],
                key="place_odds_csv"
            )

            if odds_file is not None:
                try:
                    odds_data = prepare_place_odds(odds_file)
                    results_base = attach_place_odds(predictions, odds_data)
                    matched = results_base["複勝オッズ下限"].notna().sum()
                    st.success(
                        f"複勝オッズを読み込みました：{len(odds_data):,}頭分 / "
                        f"出馬表との照合：{matched:,}頭 / {len(predictions):,}頭"
                    )
                    if matched == 0:
                        st.error("出馬表とオッズが1頭も一致しません。開催日・競馬場・レース番号・馬番を確認してください。")
                    else:
                        st.caption("オッズはレースIDから開催日・競馬場・レース番号を取得し、馬番で照合しています。")
                        threshold = st.number_input(
                            "買い候補にする保守的期待値の基準",
                            min_value=0.5, max_value=3.0, value=1.05, step=0.05,
                            help="AI3着内確率 × 複勝オッズ下限。1.00が理論上の損益分岐目安です。"
                        )
                        if st.button("🏇 複勝期待値を計算", type="primary"):
                            results = results_base.copy()
                            results["保守的期待値"] = (
                                results["AI3着内確率(%)"] / 100 * results["複勝オッズ下限"]
                            )
                            results["中央値期待値"] = (
                                results["AI3着内確率(%)"] / 100
                                * (results["複勝オッズ下限"] + results["複勝オッズ上限"]) / 2
                            )
                            results["判定"] = "判定保留"
                            has_prediction = results["AI判定"].eq("予測あり")
                            has_odds = (
                                results["複勝オッズ下限"].notna()
                                & results["複勝オッズ上限"].notna()
                                & (results["複勝オッズ下限"] >= 1)
                                & (results["複勝オッズ上限"] >= results["複勝オッズ下限"])
                            )
                            valid_rows = has_prediction & has_odds
                            results.loc[~has_prediction, "判定"] = "履歴不足"
                            results.loc[has_prediction & ~has_odds, "判定"] = "オッズ未取得"
                            results.loc[valid_rows & (results["保守的期待値"] > threshold), "判定"] = "候補"
                            results.loc[valid_rows & (results["保守的期待値"] <= threshold), "判定"] = "見送り"
                            results = results.sort_values(
                                "保守的期待値", ascending=False, na_position="last"
                            ).reset_index(drop=True)
                            results.insert(0, "順位", range(1, len(results) + 1))
                            st.dataframe(results, use_container_width=True, hide_index=True)
                            candidates = results[results["判定"].eq("候補")]
                            a, b, c = st.columns(3)
                            a.metric("分析した馬", len(results))
                            b.metric("期待値候補", len(candidates))
                            c.metric("履歴不足", int(results["判定"].eq("履歴不足").sum()))
                            if candidates.empty:
                                st.info("基準を満たす候補はありません。無理に買う必要はありません。")
                            else:
                                st.success("保守的期待値の基準を満たした候補")
                                st.dataframe(candidates, use_container_width=True, hide_index=True)
                            out = results.to_csv(index=False).encode("utf-8-sig")
                            st.download_button(
                                "分析結果をCSV保存", data=out,
                                file_name="place_ev_today_ranking.csv", mime="text/csv"
                            )
                except Exception as e:
                    st.error(f"複勝オッズCSVの処理でエラーが発生しました：{e}")
            else:
                st.info("複勝オッズCSVをアップロードすると、全馬のオッズを自動照合します。")

    except Exception as e:
        st.error(f"出馬表CSVの処理でエラーが発生しました：{e}")
else:
    st.info("TARGETの今日の出馬表CSVをアップロードすると、AI予測を確認できます。")

st.divider()
st.caption(
    "注意：この初版は複勝確率の試作モデルです。複勝オッズはTARGET出力CSVから読み込みます。"
    "AI確率・期待値は検証用であり、回収率を保証するものではありません。"
)
