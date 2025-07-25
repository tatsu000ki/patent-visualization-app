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
1. **サイドバー**で「特許 / 論文 / 技術難易度」を切替  
2. 技術難易度モードでは  
   - 指標：Composite Score / TRL / Technical Feasibility / Social Feasibility  
   - 表示単位：industry / company  
   を選択し、技術要素をフィルタ
3. 特許・論文モードは月次・国別・企業別・業界別グラフを表示
"""
)

# ───────────────────────── FILE PATHS ─────────────────────────
paths = {
    "特許": {
        "月次件数推移": "data/input/combined_patent_counts_by_month_with_flags.csv",
        "国別件数推移": "data/input/patent_country_merged_file_with_flags.csv",
        "企業別件数推移": "data/input/company_patents_merged_file_with_flags.csv",
        "業界別件数推移": "data/input/industry_patents_merged_file_with_flags.csv",
    },
    "論文": {
        "月次件数推移": "data/input/combined_paper_counts_by_month_with_flags.csv",
        "国別件数推移": "data/input/paper_country_merged_file_with_flags.csv",
        "企業別件数推移": "data/input/paper_company_merged_file_with_flags.csv",
        "業界別件数推移": "data/input/paper_industry_merged_file_with_flags.csv",
    },
}
difficulty_path = "data/input/ecosystem_analysis_result_eng.csv"

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


@st.cache_data
def load_difficulty(path: str) -> pd.DataFrame:
    """Read difficulty CSV and calculate Composite Score for each tech × industry / company"""
    df = pd.read_csv(path, encoding="utf-8").rename(
        columns={
            "technology": "technical_element",
            "TRL_tech": "TRL",
            "Technical_Feasibility_tech": "Technical_Feasibility",
            "Social_Feasibility_tech": "Social_Feasibility",
        }
    )

    # ── base-level normalisation (row wise) ──
    df["TRL_norm"]        = (df["TRL"] - 1) / 8                      # 1-9 → 0-1
    df["Tech_norm"]       = (df["Technical_Feasibility"] - 1) / 4    # 1-5 → 0-1
    df["Social_inv_norm"] = 1 - (df["Social_Feasibility"] - 1) / 4   # inverted

    # ── Composite Score for every technical element × industry / company ──
    for dim in ["industry", "company"]:
        df[f"Composite_Score_{dim}"] = (
            0.35 * (df[f"TRL_{dim}"]      - 1) / 8 +
            0.50 * (df[f"Technical_Feasibility_{dim}"] - 1) / 4 +
            0.20 * (1 - (df[f"Social_Feasibility_{dim}"] - 1) / 4)
        )

    return df


# ───────────────────────── SIDEBAR ─────────────────────────
mode = st.sidebar.selectbox("対象データ", ["特許", "論文", "技術難易度"], key="mode")

# ───────────────────────── DIFFICULTY ─────────────────────────
if mode == "技術難易度":

    metric = st.sidebar.selectbox(
        "指標",
        ["Composite_Score", "TRL", "Technical_Feasibility", "Social_Feasibility"],
        key="metric"
    )
    group_dim = st.sidebar.selectbox("表示単位", ["industry", "company"], key="group")

    df_diff = load_difficulty(difficulty_path)

    techs = st.sidebar.multiselect(
        "技術要素（複数選択可）",
        options=df_diff["technical_element"].unique().tolist(),
        default=df_diff["technical_element"].unique().tolist(),
        key="tech_sel"
    )
    if not techs:
        st.warning("少なくとも1つの技術要素を選択してください。")
        st.stop()

    df_sel = df_diff[df_diff["technical_element"].isin(techs)]

    # ── determine score column ──
    if metric == "Composite_Score":
        score_col = f"Composite_Score_{group_dim}"
    else:
        score_candidates = [f"{metric}_{group_dim}", metric]
        score_col = next((c for c in score_candidates if c in df_sel.columns), metric)

    # ── Composite Score → bar chart by tech × industry/company ──
    if metric == "Composite_Score":
        bar_tech = st.sidebar.selectbox(
            "技術要素（バーチャート用）",
            options=df_diff["technical_element"].unique().tolist(),
            key="bar_tech"
        )
        bar_df = (
            df_sel[df_sel["technical_element"] == bar_tech][["technical_element", group_dim, score_col]]
            .sort_values(score_col, ascending=False)
        )
    # bar chart display moved below score table

    # ── TRL / Technical / Social → radar chart ──
    radar_df = (
        df_sel[["technical_element", group_dim, score_col]]
        .rename(columns={score_col: "value"})
    )
    fig = px.line_polar(
        radar_df,
        theta="technical_element",
        r="value",
        color=group_dim,
        line_group=group_dim,
        line_close=True,
        category_orders={"technical_element": techs},
        title=f"{metric} レーダーチャート – {group_dim} 別",
    )
    fig.update_traces(fill="none")
    st.plotly_chart(fig, use_container_width=True)

    if metric == "Composite_Score":
        # Composite Score – bar chart below radar chart
        st.subheader(f"Composite Score – 技術要素 × {group_dim}")
        fig_bar = px.bar(
            bar_df,
            x="technical_element",
            y=score_col,
            color=group_dim,
            barmode="group",
            title=f"Composite Score by Technical Element and {group_dim.capitalize()}",
            labels={
                "technical_element": "Technical Element",
                score_col: "Score",
                group_dim: group_dim.capitalize(),
            },
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # score table (with optional evidence)
    comment_candidates = [f"{metric}_Comment_{group_dim}", f"{metric}_Comment_tech"]
    comment_col = next((c for c in comment_candidates if c in df_sel.columns), None)

    cols = ["technical_element", group_dim, score_col]
    rename_map = {
        "technical_element": "Technical Element",
        group_dim: group_dim.capitalize(),
        score_col: "Score",
    }
    if comment_col:
        cols.append(comment_col)
        rename_map[comment_col] = "Evidence"

    tbl = (
        df_sel[cols]
        .rename(columns=rename_map)
        .sort_values(["Technical Element", rename_map[group_dim]])
    )
    st.subheader(f"{metric} 各スコア" + ("と根拠" if comment_col else ""))
    st.dataframe(tbl, use_container_width=True)
    st.stop()

# ───────────────────────── PATENT / PAPER ─────────────────────────
view_mode = st.sidebar.selectbox(
    "表示タイプ",
    ["月次件数推移", "国別件数推移", "企業別件数推移", "業界別件数推移"],
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
st.caption(
    f"データソース: {paths[mode][view_mode] if mode != '技術難易度' else difficulty_path}"
)
