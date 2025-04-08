import matplotlib.pyplot as plt
import pandas as pd

# 設置中文字體（假設系統支援微軟正黑體，若無需調整可移除）
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

def create_activity_type_donut_chart(type_counts, title):
    """
    創建活動類型的環形圖
    :param type_counts: DataFrame，包含 '活動類型' 和 '次數' 兩欄
    :param title: 圖表標題
    :return: matplotlib Figure 對象
    """
    # 移除 '總計' 行
    df = type_counts[type_counts['活動類型'] != '總計'].copy()
    labels = df['活動類型']
    sizes = df['次數']
    total = sizes.sum()

    # 定義顏色（與附件圖表匹配）
    colors = ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2']

    # 創建環形圖
    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,
        colors=colors[:len(sizes)],
        startangle=90,
        wedgeprops=dict(width=0.4, edgecolor='w'),
        autopct=lambda p: f'{p:.0f}%' if p >= 1 else ''
    )

    # 添加中心文字
    centre_circle = plt.Circle((0, 0), 0.3, fc='#ADD8E6')
    fig.gca().add_artist(centre_circle)
    ax.text(0, 0.1, '院舍數目', ha='center', va='center', fontsize=12, color='black')
    ax.text(0, -0.1, str(total), ha='center', va='center', fontsize=20, color='black')

    # 添加標題
    plt.title(title, fontsize=14, pad=20)

    # 添加圖例（包含百分比）
    legend_labels = [f"{label} {size/total*100:.0f}%" for label, size in zip(labels, sizes)]
    ax.legend(wedges, legend_labels, title="活動類型", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

    # 設置最大活動類型的標籤
    max_idx = sizes.idxmax()
    max_label = f"{labels[max_idx]} {sizes[max_idx]/total*100:.0f}%"
    ax.annotate(max_label, xy=(1, 0), xytext=(1.2, 0), fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))

    # 確保圖表為圓形
    ax.axis('equal')
    return fig
