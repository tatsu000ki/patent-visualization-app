import streamlit as st
import pandas as pd
import plotly.express as px

# ワイドモード設定
st.set_page_config(layout="wide")

st.title("特許／論文件数の可視化アプリ")
st.markdown("""
- サイドバーで「対象データ」（特許／論文）と「表示タイプ」（月次／国別／企業別／業界別）を選択
- 「生データ」「6ヶ月移動平均」はチェックで表示/非表示可能
- 月次は全技術要素の動向、その他は技術要素を選んでカテゴリ別に表示
- 月次件数と累積件数を常に両方表示
""")

# -----------------------
# データ読み込み関数
# -----------------------
@st.cache_data
def load_monthly(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['year_month'] = pd.to_datetime(df['year_month'])
    df.rename(columns={'items':'count'}, inplace=True)
    # technical_element 列の統一
    if 'technical_elements' in df.columns:
        df.rename(columns={'technical_elements':'technical_element'}, inplace=True)
    if 'Technical_elements' in df.columns:
        df.rename(columns={'Technical_elements':'technical_element'}, inplace=True)
    return df[['year_month','technical_element','count','ma_6','conversion_flag']]

@st.cache_data
def load_country(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['year_month'] = pd.to_datetime(df['year_month'])
    df.rename(columns={'items':'count'}, inplace=True)
    # technical_element 列の統一
    if 'technical_elements' in df.columns:
        df.rename(columns={'technical_elements':'technical_element'}, inplace=True)
    if 'Technical_elements' in df.columns:
        df.rename(columns={'Technical_elements':'technical_element'}, inplace=True)
    # key 列は Country, company, industry いずれかを検出
    for col in ['Country','country','Company','company','industry','Industry']:
        if col in df.columns:
            df.rename(columns={col:'key'}, inplace=True)
            break
    return df[['year_month','technical_element','key','count','ma_6','conversion_flag']]

# -----------------------
# ファイルパス定義
# -----------------------
patent_monthly   = 'data/input/combined_patent_counts_by_month_with_flags.csv'
patent_country   = 'data/input/patent_country_merged_file_with_flags.csv'
patent_company   = 'data/input/company_patents_merged_file_with_flags.csv'
patent_industry  = 'data/input/industry_patents_merged_file_with_flags.csv'
paper_monthly    = 'data/input/combined_paper_counts_by_month_with_flags.csv'
paper_country    = 'data/input/paper_country_merged_file_with_flags.csv'
paper_company    = 'data/input/paper_company_merged_file_with_flags.csv'
paper_industry   = 'data/input/paper_industry_merged_file_with_flags.csv'

# -----------------------
# サイドバー: 選択
# -----------------------
kind = st.sidebar.selectbox('対象データ', ['特許','論文'], key='kind')
# 表示タイプは両方とも同じ4モード
view_mode = st.sidebar.selectbox(
    '表示タイプ',
    ['月次件数推移','国別件数推移','企業別件数推移','業界別件数推移'],
    key='view_mode'
)
show_raw = st.sidebar.checkbox('生データを表示', True, key='show_raw')
show_ma  = st.sidebar.checkbox('6ヶ月移動平均を表示', True, key='show_ma')

# -----------------------
# データロード & 技術要素選択
# -----------------------
if view_mode == '月次件数推移':
    # 全技術要素の月次推移
    path_disp = patent_monthly if kind=='特許' else paper_monthly
    df = load_monthly(path_disp)
    group_col = 'technical_element'
else:
    # 国別/企業別/業界別は技術要素ごとに表示
    if view_mode == '国別件数推移':
        path_disp = patent_country if kind=='特許' else paper_country
    elif view_mode == '企業別件数推移':
        path_disp = patent_company if kind=='特許' else paper_company
    else:  # 業界別件数推移
        path_disp = patent_industry if kind=='特許' else paper_industry
    df = load_country(path_disp)
    # 技術要素選択
    techs = df['technical_element'].dropna().unique()
    selected = st.sidebar.selectbox('技術要素選択', techs, key='tech')
    df = df[df['technical_element']==selected]
    group_col = 'key'

# -----------------------
# 前処理: ソート & 累積 & 移動平均累積
# -----------------------
df = df.sort_values([group_col,'year_month'])
df['cumulative'] = df.groupby(group_col)['count'].cumsum()
df['ma6_cum'] = df.groupby(group_col)['ma_6'].cumsum()
keys = df[group_col].unique().tolist()

# -----------------------
# 描画関数
# -----------------------
def plot_counts(y_col, title):
    fig = px.line(
        df, x='year_month', y=y_col, color=group_col,
        labels={'year_month':'年月', y_col:'件数', group_col:'カテゴリ'},
        title=title
    )
    cmap = {t.name:t.line.color for t in fig.data}
    # 移動平均線
    if show_ma:
        for k in keys:
            sub = df[df[group_col]==k]
            y_ma = 'ma_6' if y_col=='count' else 'ma6_cum'
            fig.add_scatter(
                x=sub['year_month'], y=sub[y_ma], mode='lines',
                line=dict(dash='dot', color=cmap[k]), name=f"{k} (6M MA)", legendgroup=k
            )
    # フラグマーカー
    for k in keys:
        flag = df[(df[group_col]==k)&df['conversion_flag']]
        if flag.empty:
            continue
        if show_ma:
            yv = flag['ma_6'] if y_col=='count' else flag['ma6_cum']
        elif show_raw:
            yv = flag[y_col]
        else:
            continue
        fig.add_scatter(
            x=flag['year_month'], y=yv, mode='markers',
            marker=dict(symbol='circle', size=10, color=cmap[k]),
            showlegend=False, legendgroup=k
        )
    # 生データ線非表示
    if not show_raw:
        for tr in fig.data:
            if tr.mode=='lines' and tr.name in keys:
                tr.visible=False
    fig.update_layout(legend_title_text='カテゴリ')
    st.plotly_chart(fig, use_container_width=True)

# -----------------------
# 表示
# -----------------------
st.subheader(f"{view_mode}")
plot_counts('count', f"{view_mode}")
st.subheader(f"累積{view_mode}")
plot_counts('cumulative', f"累積{view_mode}")

# -----------------------
# データ表 & フッター
# -----------------------
st.subheader('データ表')
st.dataframe(df[['year_month',group_col,'count','ma_6','conversion_flag']])
st.markdown('---')
st.caption(f"データソース: {path_disp}")
