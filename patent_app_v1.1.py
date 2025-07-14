import streamlit as st
import pandas as pd
import plotly.express as px

st.title("特許／論文件数の可視化アプリ")
st.markdown("""
- サイドバーで「対象データ」（特許／論文）と「表示タイプ」（月次／国別）を選択できます。  
- グラフの「生データ」「6ヶ月移動平均」はチェックボタンで表示/非表示を切り替え可能。  
- 凡例をクリックすると、カテゴリ（技術要素）／国単位で線・マーカーが連動して表示/非表示できます。  
- 月次件数と累積件数を常に両方表示します。
""")

@st.cache_data
def load_combined_monthly(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # 年月を datetime に
    df['year_month'] = pd.to_datetime(df['year_month'])
    # items → count
    df.rename(columns={'items': 'count'}, inplace=True)
    # カテゴリ列を technical_element に統一
    if 'category' in df.columns:
        df.rename(columns={'category': 'technical_element'}, inplace=True)
    elif 'Technical_elements' in df.columns:
        df.rename(columns={'Technical_elements': 'technical_element'}, inplace=True)
    else:
        st.error(f"technical_element に相当する列が見つかりません: {df.columns.tolist()}")
    return df[['year_month', 'technical_element', 'count', 'ma_6', 'conversion_flag']]

@st.cache_data
def load_country(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['year_month'] = pd.to_datetime(df['year_month'])
    # items → count
    df.rename(columns={'items': 'count'}, inplace=True)
    # 技術要素列を technical_element に
    if 'Technical_elements' in df.columns:
        df.rename(columns={'Technical_elements': 'technical_element'}, inplace=True)
    elif 'technical_elements' in df.columns:
        df.rename(columns={'technical_elements': 'technical_element'}, inplace=True)
    else:
        st.error(f"technical_element に相当する列が見つかりません: {df.columns.tolist()}")
    # Country → key
    if 'Country' in df.columns:
        df.rename(columns={'Country': 'key'}, inplace=True)
    elif 'country' in df.columns:
        df.rename(columns={'country': 'key'}, inplace=True)
    else:
        st.error(f"key に相当する Country 列が見つかりません: {df.columns.tolist()}")
    return df[['year_month', 'technical_element', 'key', 'count', 'ma_6', 'conversion_flag']]

# ── データファイルのパス ──
patent_monthly = 'data/input/combined_patent_counts_by_month_with_flags.csv'
patent_country = 'data/input/patent_country_merged_file_with_flags.csv'
paper_monthly  = 'data/input/combined_paper_counts_by_month_with_flags.csv'
paper_country  = 'data/input/paper_country_merged_file_with_flags.csv'

# ── サイドバーオプション ──
kind      = st.sidebar.radio('対象データ', ['特許', '論文'])
view_mode = st.sidebar.radio('表示タイプ', ['月次件数推移', '国別件数推移'])
show_raw  = st.sidebar.checkbox('生データを表示', value=True)
show_ma   = st.sidebar.checkbox('6ヶ月移動平均を表示', value=True)

# ── 選択に応じたファイルパス設定 ──
if kind == '特許':
    monthly_path = patent_monthly
    country_path = patent_country
else:
    monthly_path = paper_monthly
    country_path = paper_country

# ── データ読み込み ──
if view_mode == '月次件数推移':
    df = load_combined_monthly(monthly_path)
    group_col = 'technical_element'
else:
    df = load_country(country_path)
    techs = df['technical_element'].unique()
    selected = st.sidebar.selectbox('技術要素選択', techs)
    df = df[df['technical_element'] == selected]
    group_col = 'key'

# ── 整形：ソート＆累積計算 ──
df = df.sort_values([group_col, 'year_month'])
df['cumulative'] = df.groupby(group_col)['count'].cumsum()
keys = df[group_col].unique().tolist()

# —— 月次件数プロット —— #
st.subheader(f"{kind}：月次件数推移")
fig_monthly = px.line(
    df,
    x='year_month',
    y='count',
    color=group_col,
    labels={'count': '件数', 'year_month': '年月', group_col: 'カテゴリ'},
    title=f"{kind} 月次件数推移"
)
color_map = {t.name: t.line.color for t in fig_monthly.data}

# 6ヶ月移動平均（凡例にカテゴリ名を含める）
if show_ma:
    for k in keys:
        d = df[df[group_col] == k]
        fig_monthly.add_scatter(
            x=d['year_month'],
            y=d['ma_6'],
            mode='lines',
            line=dict(dash='dot', color=color_map[k]),
            name=f"{k} (6M MA)",
            legendgroup=k
        )

# conversion_flag マーカー
for k in keys:
    df_flag = df[(df[group_col] == k) & (df['conversion_flag'])]
    if df_flag.empty:
        continue
    if show_raw:
        y_vals = df_flag['count']
    else:
        y_vals = df_flag['ma_6']
    fig_monthly.add_scatter(
        x=df_flag['year_month'],
        y=y_vals,
        mode='markers',
        marker=dict(symbol='circle', size=10, color=color_map[k]),
        showlegend=False,
        legendgroup=k
    )

# 生データ線非表示
if not show_raw:
    for trace in fig_monthly.data:
        if trace.mode == 'lines' and trace.name in keys:
            trace.visible = False

fig_monthly.update_layout(legend_title_text='カテゴリ')
st.plotly_chart(fig_monthly, use_container_width=True)

# —— 累積件数プロット —— #
st.subheader(f"{kind}：累積件数推移")
fig_cum = px.line(
    df,
    x='year_month',
    y='cumulative',
    color=group_col,
    labels={'cumulative': '累積件数', 'year_month': '年月', group_col: 'カテゴリ'},
    title=f"{kind} 累積件数推移"
)
color_map_cum = {t.name: t.line.color for t in fig_cum.data}

# 累積移動平均線
if show_ma:
    for k in keys:
        d = df[df[group_col] == k].copy()
        d['ma6_cum'] = d['ma_6'].cumsum()
        fig_cum.add_scatter(
            x=d['year_month'],
            y=d['ma6_cum'],
            mode='lines',
            line=dict(dash='dot', color=color_map_cum[k]),
            name=f"{k} (累積6M MA)",
            legendgroup=k
        )

# 累積 conversion_flag マーカー
for k in keys:
    d = df[df[group_col] == k].copy()
    d['ma6_cum'] = d['ma_6'].cumsum()
    df_flag = d[d['conversion_flag']]
    if df_flag.empty or (not show_raw and not show_ma):
        continue
    if show_raw:
        y_vals = df_flag['cumulative']
    else:
        y_vals = df_flag['ma6_cum']
    fig_cum.add_scatter(
        x=df_flag['year_month'],
        y=y_vals,
        mode='markers',
        marker=dict(symbol='circle', size=10, color=color_map_cum[k]),
        showlegend=False,
        legendgroup=k
    )

# 生データ線非表示
if not show_raw:
    for trace in fig_cum.data:
        if trace.mode == 'lines' and trace.name in keys:
            trace.visible = False

fig_cum.update_layout(legend_title_text='カテゴリ')
st.plotly_chart(fig_cum, use_container_width=True)

# —— データ表 —— #
st.subheader('データ表')
st.dataframe(df[['year_month', group_col, 'count', 'ma_6', 'conversion_flag']])

# —— フッター —— #
st.markdown('---')
path_disp = monthly_path if view_mode == '月次件数推移' else country_path
st.caption(f"データソース: {path_disp}")
