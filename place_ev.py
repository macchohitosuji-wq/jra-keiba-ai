import streamlit as st

st.title("複勝期待値AI")

st.write("複勝オッズと3着内確率から期待値を計算します。")

st.subheader("馬の情報を入力")

horse_name = st.text_input("馬名", "テスト馬")

probability = st.number_input(
    "3着内確率（%）",
    min_value=0.0,
    max_value=100.0,
    value=60.0,
    step=1.0
)

odds_low = st.number_input(
    "複勝オッズ下限",
    min_value=1.0,
    value=1.5,
    step=0.1
)

odds_high = st.number_input(
    "複勝オッズ上限",
    min_value=1.0,
    value=2.0,
    step=0.1
)

if st.button("期待値を計算"):
    p = probability / 100
    odds_mid = (odds_low + odds_high) / 2

    ev_low = p * odds_low
    ev_mid = p * odds_mid
    ev_high = p * odds_high

    st.subheader(f"{horse_name} の計算結果")

    st.write(f"保守的期待値：{ev_low:.3f}")
    st.write(f"中央値期待値：{ev_mid:.3f}")
    st.write(f"上限期待値：{ev_high:.3f}")

    if ev_low > 1.0:
        st.success("保守的な条件でも期待値プラス")
    else:
        st.warning("現時点では見送り候補")
