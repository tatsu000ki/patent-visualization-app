import streamlit as st
import pandas as pd
import plotly.express as px

# ページ設定
st.set_page_config(layout="wide")

# タイトル・説明
st.title("特許／論文件数／技術難易度可視化アプリ")
st.markdown("""
- サイドバーで『対象データ』を選択（特許／論文／技術難易度）
- 特許／論文モード: 月次／国別／企業別／業界別グラフ
- 技術難易度モード: TRL／Technical Feasibility／Social Feasibility のレーダーチャートを業界別・企業別に表示
- 月次・累積グラフは『生データ』『6ヶ月移動平均』のチェックで切替可
""")

# ── データ読み込み関数 ──
@st.cache_data
def load_monthly(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['year_month'] = pd.to_datetime(df['year_month'])
    df.rename(columns={'items': 'count'}, inplace=True)
    # 技術要素列を統一
    if 'category' in df.columns:
        df.rename(columns={'category': 'technical_element'}, inplace=True)
    elif 'Technical_elements' in df.columns:
        df.rename(columns={'Technical_elements': 'technical_element'}, inplace=True)
    elif 'technical_elements' in df.columns:
        df.rename(columns={'technical_elements': 'technical_element'}, inplace=True)
    else:
        st.error(f"technical_element 列が見つかりません: {df.columns.tolist()}")
    return df

@st.cache_data
def load_country(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['year_month'] = pd.to_datetime(df['year_month'])
    df.rename(columns={'items': 'count'}, inplace=True)
    # 技術要素列
    if 'Technical_elements' in df.columns:
        df.rename(columns={'Technical_elements': 'technical_element'}, inplace=True)
    elif 'technical_elements' in df.columns:
        df.rename(columns={'technical_elements': 'technical_element'}, inplace=True)
    # key 列検出
    for col in ['Country','country','Company','company','industry','Industry']:
        if col in df.columns:
            df.rename(columns={col: 'key'}, inplace=True)
            break
    return df

@st.cache_data
def load_difficulty(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding='utf-8')
    df.rename(columns={
        'technology':'technical_element',
        'industry':'industry',
        'company':'company',
        'TRL_tech':'TRL',
        'Technical_Feasibility_tech':'Technical_Feasibility',
        'Social_Feasibility_tech':'Social_Feasibility'
    }, inplace=True)
    return df[['technical_element','industry','company','TRL','Technical_Feasibility','Social_Feasibility']]

# ── ファイルパス定義 ──
paths = {
    '特許':{
        '月次件数推移':'data/input/combined_patent_counts_by_month_with_flags.csv',
        '国別件数推移':'data/input/patent_country_merged_file_with_flags.csv',
        '企業別件数推移':'data/input/company_patents_merged_file_with_flags.csv',
        '業界別件数推移':'data/input/industry_patents_merged_file_with_flags.csv'
    },
    '論文':{
        '月次件数推移':'data/input/combined_paper_counts_by_month_with_flags.csv',
        '国別件数推移':'data/input/paper_country_merged_file_with_flags.csv',
        '企業別件数推移':'data/input/paper_company_merged_file_with_flags.csv',
        '業界別件数推移':'data/input/paper_industry_merged_file_with_flags.csv'
    }
}
difficulty_path = 'data/input/ecosystem_analysis_result_eng.csv'

# ── サイドバー: 対象データ選択 ──
mode = st.sidebar.selectbox('対象データ', ['特許','論文','技術難易度'], key='mode')

# ── 技術難易度モード ──
if mode == '技術難易度':
    metric = st.sidebar.selectbox('指標', ['TRL','Technical_Feasibility','Social_Feasibility'], key='metric')
    group_dim = st.sidebar.selectbox('表示単位', ['industry','company'], key='group')
    df_diff = load_difficulty(difficulty_path)
    techs = df_diff['technical_element'].unique().tolist()
    base = pd.DataFrame({'technical_element': techs})
    dfs = []
    for grp in df_diff[group_dim].dropna().unique():
        tmp = base.merge(
            df_diff[df_diff[group_dim]==grp][['technical_element', metric]],
            on='technical_element', how='left'
        ).fillna(0)
        tmp[group_dim] = grp
        dfs.append(tmp)
    radar_df = pd.concat(dfs, ignore_index=True)
    fig = px.line_polar(
        radar_df,
        theta='technical_element',
        r=metric,
        color=group_dim,
        line_close=True,
        category_orders={'technical_element': techs},
        title=f"技術難易度レーダーチャート ({metric}) - {group_dim}別"
    )
    fig.update_traces(fill='toself')
    st.plotly_chart(fig, use_container_width=True)
    st.stop()

# ── 特許/論文モード ──
view_mode = st.sidebar.selectbox('表示タイプ', ['月次件数推移','国別件数推移','企業別件数推移','業界別件数推移'], key='view')
show_raw = st.sidebar.checkbox('生データを表示', True, key='raw')
show_ma  = st.sidebar.checkbox('6ヶ月移動平均を表示', True, key='ma')

# データ読み込み
if view_mode == '月次件数推移':
    df = load_monthly(paths[mode][view_mode])
    group_col = 'technical_element'
else:
    df = load_country(paths[mode][view_mode])
    sel = st.sidebar.selectbox('技術要素選択', df['technical_element'].unique(), key='tech')
    df = df[df['technical_element']==sel]
    group_col = 'key'

# 【デバッグ表示】データフレーム内容確認
st.write('### デバッグ：読み込まれたデータフレーム')
st.write(df.head())
st.write('Columns:', df.columns.tolist())

# 前処理: 重複カラム除去＆ソート: 重複カラム除去＆ソート
df = df.loc[:, ~df.columns.duplicated()]
df = df.sort_values([group_col,'year_month'])
# 累積計算
df['cumulative'] = df.groupby(group_col)['count'].cumsum()
# 移動平均累積 (全モード対応)
df['ma6_cum'] = df.groupby(group_col)['ma_6'].cumsum()
# グループキー一覧
keys = df[group_col].unique().tolist()

# グラフ描画関数
def plot_counts(y_col, title):
    fig = px.line(
        df, x='year_month', y=y_col, color=group_col,
        labels={'year_month':'年月', y_col:'件数', group_col:'カテゴリ'},
        title=title
    )
    cmap = {t.name:t.line.color for t in fig.data}
    # 移動平均線
    if show_ma and y_col in ['count','cumulative']:
        for k in keys:
            d = df[df[group_col]==k]
            y_ma = 'ma_6' if y_col=='count' else 'ma6_cum'
            fig.add_scatter(
                x=d['year_month'], y=d[y_ma], mode='lines',
                line=dict(dash='dot', color=cmap[k]), name=f"{k} (6M MA)", legendgroup=k
            )
    # フラグマーカー
    for k in keys:
        fl = df[(df[group_col]==k)&df['conversion_flag']]
        if fl.empty: continue
        if show_ma and y_col in ['count','cumulative']:
            yv = fl['ma_6'] if y_col=='count' else fl['ma6_cum']
        elif show_raw:
            yv = fl[y_col]
        else:
            continue
        fig.add_scatter(
            x=fl['year_month'], y=yv, mode='markers',
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

# 月次＆累積プロット
st.subheader(view_mode)
plot_counts('count', view_mode)
st.subheader(f"累積{view_mode}")
plot_counts('cumulative', f"累積{view_mode}")

# データ表＆フッター
st.subheader('データ表')
st.dataframe(df[['year_month', group_col, 'count','ma_6','conversion_flag','cumulative']])
st.markdown('---')
st.caption(f"データソース: {paths[mode][view_mode] if mode!='技術難易度' else difficulty_path}")
