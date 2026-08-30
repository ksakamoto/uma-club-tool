"""重みづけ調整ページ：各観点のスコアは固定、重みだけ変えて総合点を再計算。"""
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

from app.core.session_init import ensure_session
from app.scoring.registry import discover_rules

ensure_session()

st.title("⚙️ 重みづけ調整")

if "scored_df" not in st.session_state:
    st.warning("先にデータ準備ページで採点を完了してください")
    st.stop()

scored_df: pd.DataFrame = st.session_state["scored_df"].copy()
score_cols = [c for c in scored_df.columns if c.startswith("score_")]
rule_names = [c.replace("score_", "") for c in score_cols]

# ルールのラベル情報を取得
all_rules = discover_rules()
rule_meta = {cls.name: cls for cls in all_rules}

# --- デフォルト重みをconfig.yamlから読む ---
config_path = Path(__file__).parent.parent.parent / "config.yaml"
default_weights: dict = {}
presets: dict = {}
if config_path.exists():
    cfg = yaml.safe_load(config_path.read_text())
    default_weights = cfg.get("scoring", {}).get("weights", {})
    presets = cfg.get("scoring", {}).get("presets", {})

st.markdown("""
各観点のスコア（0〜100点）はデータ準備ページで確定済みです。
ここでは**各観点に何%の重みをかけるか**を調整して総合点を変動させます。
""")

# --- 現在の観点スコアのサマリー ---
with st.expander("各観点スコアのサマリー（参考）", expanded=False):
    summary = {}
    for col in score_cols:
        name = col.replace("score_", "")
        label = rule_meta[name].label if name in rule_meta else name
        summary[label] = {
            "平均": round(scored_df[col].mean(), 1),
            "最高": round(scored_df[col].max(), 1),
            "最低": round(scored_df[col].min(), 1),
        }
    st.dataframe(pd.DataFrame(summary).T, use_container_width=True)

st.divider()

# --- プリセット ---
preset_labels = {
    "カスタム": "カスタム",
    "balanced": "バランス型",
    "pedigree_focus": "血統重視",
    "value_hunt": "割安狙い",
}
selected_preset = st.selectbox(
    "プリセット",
    ["カスタム"] + list(presets.keys()),
    format_func=lambda k: preset_labels.get(k, k),
)

if selected_preset != "カスタム" and selected_preset in presets:
    current_weights = presets[selected_preset]
else:
    current_weights = st.session_state.get("scoring_weights", default_weights)

# --- 重みスライダー ---
st.header("重みの調整")
st.caption("合計が100%になるように自動正規化されます")

enabled_rules = st.multiselect(
    "使用する観点",
    options=rule_names,
    default=rule_names,
    format_func=lambda n: rule_meta[n].label if n in rule_meta else n,
)

raw_weights: dict[str, int] = {}
for name in enabled_rules:
    label = rule_meta[name].label if name in rule_meta else name
    default_val = int(current_weights.get(name, 1.0 / len(rule_names)) * 100)
    raw_weights[name] = st.slider(f"{label}", 0, 100, max(1, default_val), step=5)

weight_sum = sum(raw_weights.values())
if weight_sum == 0:
    st.error("重みの合計が0です")
    st.stop()

weights = {name: v / weight_sum for name, v in raw_weights.items()}

normalized_display = {
    (rule_meta[n].label if n in rule_meta else n): f"{round(v * 100, 1)}%"
    for n, v in weights.items()
}
st.json(normalized_display)

# --- 総合点の再計算 ---
st.divider()
if st.button("🔄 この重みで総合点を再計算", type="primary"):
    df = st.session_state["scored_df"].copy()

    new_totals = pd.Series(0.0, index=df.index)
    for name, w in weights.items():
        col = f"score_{name}"
        if col in df.columns:
            new_totals += df[col] * w

    df["total_score"] = new_totals.round(1)
    df = df.sort_values("total_score", ascending=False).reset_index(drop=True)

    st.session_state["scored_df"] = df
    st.session_state["scoring_weights"] = weights

    st.success("総合点を更新しました！候補一覧ページで確認してください。")
    display_cols = ["horse_name", "total_score"] + score_cols
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[display_cols].head(10), use_container_width=True)
