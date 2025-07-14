import streamlit as st
import pandas as pd
import plotly.express as px

st.title("特許件数の可視化アプリ")
st.markdown("""
- サイドバーで表示するデータタイプを選択できます。
- 折れ線グラフの「生データ」「6ヶ月移動平均」はそれぞれチェックボックスで表示/非表示を切り替えられます。
- グラフの凡例をクリックすると、カテゴリ単位で線とマーカーが連動してオン/オフできます。
- 月次件数と累積件数を常に両方表示します。
""")

@st.cache_data
def load_combined_monthly(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['year_month'] = pd.to_datetime(df['year_month'])
    df.rename(columns={'category':'key','items':'count'}, inplace=True)
    return df[['year_month','key','count','ma_6','conversion_flag']]

@st.cache_data
def load_country(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    first_col = df.columns[0]
    df['year_month'] = pd.to_datetime(df[first_col])
    cols = df.columns.tolist()
    tech = next((c for c in cols if 'technical' in c.lower()), None)
    itm  = next((c for c in cols if 'item'      in c.lower()), None)
    cty  = next((c for c in cols if 'country'   in c.lower()), None)
    ma   = next((c for c in cols if 'ma_6'      in c.lower()), None)
    flg  = next((c for c in cols if 'flag'      in c.lower()), None)
    rename_map = {}
    if tech: rename_map[tech] = 'technical_element'
    if itm:  rename_map[itm]  = 'count'
    if cty:  rename_map[cty]  = 'key'
    if ma:   rename_map[ma]   = 'ma_6'
    if flg:  rename_map[flg]  = 'conversion_flag'
    df.rename(columns=rename_map, inplace=True)
    return df[['year_month','technical_element','key','count','ma_6','conversion_flag']]

monthly_path = 'data/input/combined_patent_counts_by_month_with_flags.csv'
country_path = 'data/input/patent_country_merged_file_with_flags.csv'

# サイドバー：オプション
data_type = st.sidebar.radio(
    '表示するデータタイプ',
    ('月次特許件数推移','国別特許件数推移')
)
show_raw = st.sidebar.checkbox('生データを表示', value=True)
show_ma  = st.sidebar.checkbox('6ヶ月移動平均を表示', value=True)

# データ読み込み
if data_type == '月次特許件数推移':
    df = load_combined_monthly(monthly_path)
else:
    df = load_country(country_path)
    techs = df['technical_element'].unique()
    selected = st.sidebar.selectbox('技術要素選択', techs)
    df = df[df['technical_element'] == selected]

# 整形：ソート＆累積計算
df = df.sort_values(['key','year_month'])
df['cumulative'] = df.groupby('key')['count'].cumsum()

keys = df['key'].unique().tolist()

# —— 月次特許件数プロット —— #
st.subheader('月次特許件数')
fig_monthly = px.line(
    df, x='year_month', y='count', color='key',
    labels={'count':'特許件数','year_month':'年月','key':'カテゴリ'},
    title='月次特許件数推移'
)
color_map = {t.name: t.line.color for t in fig_monthly.data}

# 移動平均線を追加
if show_ma:
    for k in keys:
        d = df[df['key']==k]
        fig_monthly.add_scatter(
            x=d['year_month'], y=d['ma_6'],
            mode='lines',
            line=dict(dash='dot', color=color_map[k]),
            name='6ヶ月移動平均',
            legendgroup=k
        )

# conversion_flag マーカー（月次）
for k in keys:
    df_flag = df[(df['key']==k) & (df['conversion_flag'])]
    if df_flag.empty:
        continue
    if show_raw:
        y_vals = df_flag['count']
    elif show_ma:
        y_vals = df_flag['ma_6']
    else:
        continue
    fig_monthly.add_scatter(
        x=df_flag['year_month'], y=y_vals,
        mode='markers',
        marker=dict(symbol='circle', size=10, color=color_map[k]),
        showlegend=False,
        legendgroup=k
    )

# 生データ線を非表示にする
if not show_raw:
    for trace in fig_monthly.data:
        if trace.mode=='lines' and trace.name in keys:
            trace.visible = False

fig_monthly.update_layout(legend_title_text='カテゴリ')
st.plotly_chart(fig_monthly, use_container_width=True)

# —— 累積特許件数プロット —— #
st.subheader('累積特許件数')
fig_cum = px.line(
    df, x='year_month', y='cumulative', color='key',
    labels={'cumulative':'累積特許件数','year_month':'年月','key':'カテゴリ'},
    title='累積特許件数推移'
)
color_map_cum = {t.name: t.line.color for t in fig_cum.data}

# 累積移動平均線を追加
if show_ma:
    for k in keys:
        d = df[df['key']==k].copy()
        d['ma6_cum'] = d['ma_6'].cumsum()
        fig_cum.add_scatter(
            x=d['year_month'], y=d['ma6_cum'],
            mode='lines',
            line=dict(dash='dot', color=color_map_cum[k]),
            name='累積6ヶ月移動平均',
            legendgroup=k
        )

# conversion_flag マーカー（累積）
for k in keys:
    d = df[df['key']==k].copy()
    d['ma6_cum'] = d['ma_6'].cumsum()
    df_flag = d[d['conversion_flag']]
    if df_flag.empty or (not show_raw and not show_ma):
        continue
    if show_raw:
        y_vals = df_flag['cumulative']
    else:
        y_vals = df_flag['ma6_cum']
    fig_cum.add_scatter(
        x=df_flag['year_month'], y=y_vals,
        mode='markers',
        marker=dict(symbol='circle', size=10, color=color_map_cum[k]),
        showlegend=False,
        legendgroup=k
    )

# 生データ線を非表示にする
if not show_raw:
    for trace in fig_cum.data:
        if trace.mode=='lines' and trace.name in keys:
            trace.visible = False

fig_cum.update_layout(legend_title_text='カテゴリ')
st.plotly_chart(fig_cum, use_container_width=True)

# —— データ表 —— #
st.subheader('データ表')
st.dataframe(df[['year_month','key','count','ma_6','conversion_flag']])

# —— フッター —— #
st.markdown('---')
path_disp = monthly_path if data_type.startswith('月次') else country_path
st.caption(f"データソース: {path_disp}")
