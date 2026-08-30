import streamlit as st
import pandas as pd


def render_horse_card(row: pd.Series, score_cols: list[str]) -> None:
    total = row["total_score"]
    color = "🟢" if total >= 70 else "🟡" if total >= 50 else "🔴"

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### {color} {row['horse_name']}")
        st.markdown(
            f"**父:** {row.get('sire_name', '-')} ｜ "
            f"**調教師:** {row.get('trainer_name', '-')} ({row.get('stable', '-')}) ｜ "
            f"**牧場:** {row.get('farm_name', '-')}"
        )
        if score_cols:
            bar_data = {c.replace("score_", ""): row[c] for c in score_cols if c in row}
            bar_df = pd.DataFrame({"スコア": bar_data})
            st.bar_chart(bar_df, height=120)

    with col2:
        price = row.get("price_total")
        price_str = f"{int(price):,}万円" if pd.notna(price) else "-"
        st.metric("総合スコア", f"{total:.1f}")
        st.metric("募集額", price_str)
        st.caption(row.get("sex", ""))
