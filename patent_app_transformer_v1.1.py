# -*- coding: utf-8 -*-
"""
Streamlit app – patent / paper trends & technical-difficulty dashboard
Composite Score (TRL 0.35  + Technical 0.50  + Social_inv 0.20)
is calculated **per technical element × industry / company**.
"""
import streamlit as st
import pandas as pd          # type: ignore
import plotly.express as px  # type: ignore

# ───────────────────────── UI SET-UP ─────────────────────────
st.set_page_config(layout="wide")
st.title("特許／論文件数／技術難易度可視化アプリ")
st.markdown(
    """
### 使い方

"""
)

# ───────────────────────── FILE PATHS ─────────────────────────
paths = {
    "特許": {
        "月次件数推移": "data/input/transformer1/combined_patent_counts_by_month_transfomer1.csv",
        "国別件数推移": "data/input/transformer1/patent_country_merged_file_transformer1.csv",
    },
    "論文": {
        "月次件数推移": "data/input/transformer1/combined_paper_counts_by_month_with_flags_transformer1.csv",
        "国別件数推移": "data/input/transformer1/paper_country_merged_file_with_flags_transformer1.csv",
    },
}

# ───────────────────────── LOADERS ─────────────────────────
@st.cache_data
def load_monthly(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["year_month"] = pd.to_datetime(df["year_month"], errors="coerce")

    rename_map = {"items": "count"}
    if "category" in df:
        rename_map["category"] = "technical_element"
    if "Technical_elements" in df:
        rename_map["Technical_elements"] = "technical_element"
    if "technical_elements" in df:
        rename_map["technical_elements"] = "technical_element"
    df.rename(columns=rename_map, inplace=True)
    return df


@st.cache_data
def load_country(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["year_month"] = pd.to_datetime(df["year_month"], errors="coerce")
    df.rename(columns={"items": "count"}, inplace=True)
    if "Technical_elements" in df:
        df.rename(columns={"Technical_elements": "technical_element"}, inplace=True)
    if "technical_elements" in df:
        df.rename(columns={"technical_elements": "technical_element"}, inplace=True)

    # 列名を key に統一
    for c in ["Country", "country", "Company", "company", "industry", "Industry"]:
        if c in df.columns:
            df.rename(columns={c: "key"}, inplace=True)
            break
    return df



# ───────────────────────── SIDEBAR ─────────────────────────
mode = st.sidebar.selectbox("対象データ", ["特許", "論文"], key="mode")


# ───────────────────────── PATENT / PAPER ─────────────────────────
view_mode = st.sidebar.selectbox(
    "表示タイプ",
    ["月次件数推移", "国別件数推移"],
    key="view",
)
show_raw = st.sidebar.checkbox("生データを表示", True, key="raw")
show_ma  = st.sidebar.checkbox("6ヶ月移動平均を表示", True, key="ma")

if view_mode == "月次件数推移":
    df = load_monthly(paths[mode][view_mode])
    group_col = "technical_element"
else:
    df = load_country(paths[mode][view_mode])
    sel = st.sidebar.selectbox("技術要素選択", df["technical_element"].unique(), key="tech")
    df  = df[df["technical_element"] == sel]
    group_col = "key"

df = df.loc[:, ~df.columns.duplicated()].sort_values([group_col, "year_month"])
df["cumulative"] = df.groupby(group_col)["count"].cumsum()
df["ma6_cum"]    = df.groupby(group_col)["ma_6"].cumsum()
keys = df[group_col].unique().tolist()


def plot_counts(y: str, title: str) -> None:
    fig = px.line(
        df,
        x="year_month",
        y=y,
        color=group_col,
        labels={"year_month": "年月", y: "件数", group_col: "カテゴリ"},
        title=title,
    )
    cmap = {t.name: t.line.color for t in fig.data}

    # 6-month MA
    if show_ma and y in {"count", "cumulative"}:
        for k in keys:
            d = df[df[group_col] == k]
            yma = "ma_6" if y == "count" else "ma6_cum"
            fig.add_scatter(
                x=d["year_month"],
                y=d[yma],
                mode="lines",
                line=dict(dash="dot", color=cmap[k]),
                name=f"{k} (6M MA)",
                legendgroup=k,
            )

    # conversion_flag markers
    for k in keys:
        fl = df[(df[group_col] == k) & df["conversion_flag"]]
        if fl.empty:
            continue
        if show_ma and y in {"count", "cumulative"}:
            yv = fl["ma_6"] if y == "count" else fl["ma6_cum"]
        elif show_raw:
            yv = fl[y]
        else:
            continue
        fig.add_scatter(
            x=fl["year_month"],
            y=yv,
            mode="markers",
            marker=dict(symbol="circle", size=10, color=cmap[k]),
            showlegend=False,
            legendgroup=k,
        )

    # hide raw lines when unchecked
    if not show_raw:
        for tr in fig.data:
            if tr.mode == "lines" and tr.name in keys:
                tr.visible = False

    fig.update_layout(legend_title_text="カテゴリ")
    st.plotly_chart(fig, use_container_width=True)


st.caption(f"データ数: {len(df)} 件")
st.subheader(view_mode)
plot_counts("count", view_mode)
st.subheader(f"累積{view_mode}")
plot_counts("cumulative", f"累積{view_mode}")

st.subheader("データ表")
st.dataframe(
    df[
        ["year_month", group_col, "count", "ma_6", "conversion_flag", "cumulative"]
    ],
    use_container_width=True,
)
st.markdown("---")
