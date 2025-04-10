import plotly.graph_objects as go
import pandas as pd

def create_activity_type_donut_chart(type_counts, title):
    """
    創建活動類型的環形圖（使用 Plotly）
    :param type_counts: DataFrame，包含 '活動類型' 和 '次數' 兩欄
    :param title: 圖表標題
    :return: Plotly Figure 對象
    """
    # 移除 '總計' 行
    df = type_counts[type_counts['活動類型'] != '總計'].copy()
    labels = df['活動類型']
    values = df['次數']
    total = values.sum()

    # 定義顏色（與附件圖表匹配）
    colors = ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2']

    # 計算百分比
    percentages = [value / total * 100 for value in values]
    hover_text = [f"{label}: {value} 次 ({percent:.0f}%)" for label, value, percent in zip(labels, values, percentages)]

    # 創建環形圖
    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,  # 設置環形圖的中心孔大小
            marker=dict(colors=colors[:len(values)], line=dict(color='#FFFFFF', width=2)),
            textinfo='label+percent',  # 顯示活動類型和百分比
            textposition='auto',  # 自動決定標籤位置（內部或外部）
            insidetextorientation='horizontal',  # 強制內部標籤水平顯示
            hoverinfo='text',
            hovertext=hover_text,
            textfont=dict(size=16, family='Microsoft JhengHei, sans-serif'),  # 保持字體大小為 16
        )
    ])

    # 添加中心文字
    fig.add_annotation(
        text="院舍數目",
        x=0.5,
        y=0.55,
        showarrow=False,
        font=dict(size=18, family='Microsoft JhengHei, sans-serif')  # 保持字體大小為 18
    )
    fig.add_annotation(
        text=str(total),
        x=0.5,
        y=0.45,
        showarrow=False,
        font=dict(size=28, family='Microsoft JhengHei, sans-serif')  # 保持字體大小為 28
    )

    # 設置圖表佈局
    fig.update_layout(
        title=dict(text=title, font=dict(size=24, family='Microsoft JhengHei, sans-serif'), x=0.5, xanchor='center'),  # 保持標題字體大小為 24
        showlegend=True,
        legend=dict(
            title=dict(text="活動類型", font=dict(size=18, family='Microsoft JhengHei, sans-serif')),
            font=dict(size=18, family='Microsoft JhengHei, sans-serif'),  # 保持圖例字體大小為 18
            x=1.4,  # 將圖例進一步向右移動，避免與標籤重疊
            y=0.5,
            traceorder='normal'
        ),
        margin=dict(t=200, b=100, l=100, r=300),  # 保持邊距，確保外部標籤有空間
        width=800,  # 縮小圖表寬度
        height=600,  # 縮小圖表高度
        font=dict(family='Microsoft JhengHei, sans-serif', size=16)
    )

    return fig
