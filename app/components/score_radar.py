import streamlit as st
import plotly.graph_objects as go


def render_score_radar(scores: dict[str, float], title: str = "") -> None:
    categories = list(scores.keys())
    values = [scores[c] for c in categories]

    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        name=title,
        line_color="royalblue",
        fillcolor="rgba(65, 105, 225, 0.2)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        height=350,
        margin=dict(t=30, b=30, l=30, r=30),
    )
    st.plotly_chart(fig, use_container_width=True)
