import plotly.graph_objects as go
import pandas as pd
import numpy as np

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

    # 創建環形圖，禁用自動標籤
    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,  # 設置環形圖的中心孔大小
            marker=dict(colors=colors[:len(values)], line=dict(color='#FFFFFF', width=2)),
            textinfo='none',  # 禁用自動標籤
            hoverinfo='text',
            hovertext=hover_text,
        )
    ])

    # 計算每個區塊的角度（用於定位標籤）
    cumulative_values = np.cumsum([0] + list(values))
    total_value = sum(values)
    angles = [(cumulative_values[i] + cumulative_values[i+1]) / 2 / total_value * 360 for i in range(len(values))]

    # 添加手動標籤（活動類型和百分比）
    annotations = []
    for i, (label, percent, angle) in enumerate(zip(labels, percentages, angles)):
        # 將角度轉換為弧度
        rad = np.deg2rad(angle)
        # 計算標籤的半徑（距離中心的位置）
        radius = 1.2 if percent < 5 else 0.8  # 小於 5% 的標籤放在外部，否則內部
        # 計算標籤的 x, y 位置
        x = radius * np.cos(rad)
        y = radius * np.sin(rad)
        # 調整標籤的對齊方式
        xanchor = 'left' if 90 <= angle <= 270 else 'right'
        yanchor = 'middle'

        # 添加活動類型標籤
        annotations.append(
            dict(
                x=x,
                y=y,
                text=label,
                showarrow=False,
                xanchor=xanchor,
                yanchor=yanchor,
                font=dict(size=14, family='Microsoft JhengHei, sans-serif'),
                align='center',
            )
        )

        # 添加百分比標籤（放在更外側）
        percent_radius = radius + 0.2
        x_percent = percent_radius * np.cos(rad)
        y_percent = percent_radius * np.sin(rad)
        annotations.append(
            dict(
                x=x_percent,
                y=y_percent,
                text=f"{percent:.0f}%",
                showarrow=False,
                xanchor=xanchor,
                yanchor=yanchor,
                font=dict(size=14, family='Microsoft JhengHei, sans-serif'),
                align='center',
            )
        )

    # 添加中心文字
    annotations.append(
        dict(
            text="院舍數目",
            x=0.5,
            y=0.55,
            showarrow=False,
            font=dict(size=18, family='Microsoft JhengHei, sans-serif')
        )
    )
    annotations.append(
        dict(
            text=str(total),
            x=0.5,
            y=0.45,
            showarrow=False,
            font=dict(size=28, family='Microsoft JhengHei, sans-serif')
        )
    )

    # 設置圖表佈局
    fig.update_layout(
        title=dict(text=title, font=dict(size=24, family='Microsoft JhengHei, sans-serif'), x=0.5, xanchor='center'),
        showlegend=True,
        legend=dict(
            title=dict(text="活動類型", font=dict(size=18, family='Microsoft JhengHei, sans-serif')),
            font=dict(size=18, family='Microsoft JhengHei, sans-serif'),
            x=1.2,
            y=0.5,
            traceorder='normal'
        ),
        margin=dict(t=150, b=100, l=100, r=250),  # 增加邊距，特別是上邊距和右邊距
        width=1000,  # 增加圖表寬度
        height=700,  # 增加圖表高度
        font=dict(family='Microsoft JhengHei, sans-serif', size=16),
        annotations=annotations
    )

    return fig
