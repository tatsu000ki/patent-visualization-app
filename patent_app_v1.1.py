import streamlit as st
import pandas as pd
import plotly.express as px

st.title("特許件数の可視化アプリ")
st.markdown("""
- サイドバーで表示するデータタイプを選択できます。
- グラフの凡例をクリックすると表示対象のオン/オフが切り替わります（移動平均も連動します）。
- 月次件数と累積件数を常に両方表示します。
""")

@st.cache_data
def load_combined_monthly(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # 年月を自動パース（YYYY-MM も YYYY-MM-DD もOK）
    df['year_month'] = pd.to_datetime(df['year_month'])
    # カラムの統一: category→key, items→count
    df.rename(columns={'category': 'key', 'items': 'count'}, inplace=True)
    return df[['year_month', 'key', 'count', 'ma_6', 'conversion_flag']]

@st.cache_data
def load_country(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # 先頭列を日付として自動パース
    first_col = df.columns[0]
    df['year_month'] = pd.to_datetime(df[first_col])
    # カラム名を自動検出してリネーム
    cols = df.columns.tolist()
    tech_col    = next((c for c in cols if 'technical' in c.lower()), None)
    item_col    = next((c for c in cols if 'item'      in c.lower()), None)
    country_col = next((c for c in cols if 'country'   in c.lower()), None)
    ma_col      = next((c for c in cols if 'ma_6'      in c.lower()), None)
    flag_col    = next((c for c in cols if 'flag'      in c.lower()), None)

    rename_map = {}
    if tech_col:    rename_map[tech_col]    = 'technical_element'
    if item_col:    rename_map[item_col]    = 'count'
    if country_col: rename_map[country_col] = 'key'
    if ma_col:      rename_map[ma_col]      = 'ma_6'
    if flag_col:    rename_map[flag_col]    = 'conversion_flag'
    df.rename(columns=rename_map, inplace=True)

    return df[['year_month', 'technical_element', 'key', 'count', 'ma_6', 'conversion_flag']]

# — ファイルパス（_with_flags.csv版） —
monthly_path = 'data/input/combined_patent_counts_by_month_with_flags.csv'
country_path = 'data/input/patent_country_merged_file_with_flags.csv'

# — サイドバー設定 —
data_type = st.sidebar.radio(
    '表示するデータタイプ',
    ('月次特許件数推移', '国別特許件数推移')
)
show_ma = st.sidebar.checkbox('6ヶ月移動平均を表示', value=True)

# — データ読み込み & 整形 —
if data_type == '月次特許件数推移':
    df = load_combined_monthly(monthly_path)
else:
    df = load_country(country_path)
    techs = df['technical_element'].unique()
    selected_tech = st.sidebar.selectbox('技術要素選択', techs)
    df = df[df['technical_element'] == selected_tech]

# 並び替え & 累積列
df = df.sort_values(['key', 'year_month'])
df['cumulative'] = df.groupby('key')['count'].cumsum()

# — 月次特許件数プロット —
st.subheader('月次特許件数')
fig_monthly = px.line(
    df,
    x='year_month', y='count', color='key',
    labels={'count': '特許件数', 'year_month': '年月', 'key': 'カテゴリ'},
    title='月次特許件数推移'
)
# ベースの色マッピング
color_map = {trace.name: trace.line.color for trace in fig_monthly.data}

# 移動平均線（細かい点線）を追加
if show_ma:
    for k in df['key'].unique():
        d = df[df['key'] == k]
        fig_monthly.add_scatter(
            x=d['year_month'], y=d['ma_6'],
            mode='lines',
            line=dict(dash='dot', color=color_map[k]),
            name='6ヶ月移動平均',
            legendgroup=k
        )

# conversion_flag=true の〇マーカーを追加
for k in df['key'].unique():
    d_flag = df[(df['key'] == k) & (df['conversion_flag'] == True)]
    fig_monthly.add_scatter(
        x=d_flag['year_month'], y=d_flag['count'],
        mode='markers',
        marker=dict(symbol='circle', size=10, color=color_map[k]),
        showlegend=False,
        legendgroup=k
    )

fig_monthly.update_layout(legend_title_text='カテゴリ')
st.plotly_chart(fig_monthly, use_container_width=True)

# — 累積特許件数プロット —
st.subheader('累積特許件数')
fig_cum = px.line(
    df,
    x='year_month', y='cumulative', color='key',
    labels={'cumulative': '累積特許件数', 'year_month': '年月', 'key': 'カテゴリ'},
    title='累積特許件数推移'
)
# 色マップ（累積）
color_map_cum = {trace.name: trace.line.color for trace in fig_cum.data}

# 累積移動平均線（オプション）
if show_ma:
    for k in df['key'].unique():
        d = df[df['key'] == k].copy()
        d['ma6_cum'] = d['ma_6'].cumsum()
        fig_cum.add_scatter(
            x=d['year_month'], y=d['ma6_cum'],
            mode='lines',
            line=dict(dash='dot', color=color_map_cum[k]),
            name='累積6ヶ月移動平均',
            legendgroup=k
        )

# 累積 conversion_flag マーカー
for k in df['key'].unique():
    d_flag = df[(df['key'] == k) & (df['conversion_flag'] == True)]
    fig_cum.add_scatter(
        x=d_flag['year_month'], y=d_flag['cumulative'],
        mode='markers',
        marker=dict(symbol='circle', size=10, color=color_map_cum[k]),
        showlegend=False,
        legendgroup=k
    )

fig_cum.update_layout(legend_title_text='カテゴリ')
st.plotly_chart(fig_cum, use_container_width=True)

# — データ表 —
st.subheader('データ表')
st.dataframe(df[['year_month', 'key', 'count', 'ma_6', 'conversion_flag']])

# — フッター —
st.markdown('---')
path_display = monthly_path if data_type == '月次特許件数推移' else country_path
st.caption(f"データソース: {path_display}")
