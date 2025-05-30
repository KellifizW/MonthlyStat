import streamlit as st
import pandas as pd
import requests
from io import StringIO
import re
import graph  # 假設你已有 graph.py

# 設置頁面為寬屏模式
st.set_page_config(layout="wide")

# GitHub Raw URL
RAW_URL = "https://raw.githubusercontent.com/KellifizW/MonthlyStat/main/homelist.csv"

# 定義必要欄位
REQUIRED_COLUMNS = ['RespStaff', '2ndRespStaffName', 'HomeName', 'ServiceDate']

# 名稱轉換字典
NAME_CONVERSION = {
    '溫?邦': 'Pong',
    '溫晧邦': 'Pong',
    '譚惠凌': 'Ling',
    '陳發成': 'Jack',
    '林振聲': 'Mike',
    '黃瑞霞': 'Peppy',
    '曾嘉欣': 'Kama',
    '徐家兒': 'Kayi'
}

# 初始化 session_state
if 'uploaded_df' not in st.session_state:
    st.session_state['uploaded_df'] = None
if 'used_encoding' not in st.session_state:
    st.session_state['used_encoding'] = None

# 通用檔案讀取函數（支援 CSV 和 XLSX）
def read_file(file):
    file.seek(0)
    file_name = file.name.lower()

    if file_name.endswith('.csv'):
        encoding = 'big5hkscs'
        separators = [',', '\t']
        sample = file.read(1024).decode(encoding, errors='replace')
        file.seek(0)
        separator = max(separators, key=lambda sep: sample.count(sep))

        try:
            df = pd.read_csv(file, encoding=encoding, sep=separator, on_bad_lines='warn')
            return df, encoding
        except Exception as e:
            st.error(f"無法讀取 CSV 檔案，請檢查檔案是否有效: {str(e)}")
            return None, None

    elif file_name.endswith('.xlsx'):
        try:
            df = pd.read_excel(file, engine='openpyxl')
            return df, 'utf-8'
        except Exception as e:
            st.error(f"無法讀取 XLSX 檔案，請檢查檔案是否有效: {str(e)}")
            return None, None

    else:
        st.error("不支援的檔案格式，請上傳 .csv 或 .xlsx 檔案")
        return None, None

# 從 GitHub 讀取 homelist.csv
def get_github_csv_data(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = StringIO(response.text)
            df = pd.read_csv(data)
            return df
        else:
            st.error(f"無法獲取 GitHub CSV 檔案，狀態碼：{response.status_code}")
            return None
    except Exception as e:
        st.error(f"讀取 GitHub CSV 時發生錯誤：{str(e)}")
        return None

# 提取 HomeName 的前 1-3 個數字
def extract_home_number(home_name):
    if pd.isna(home_name):
        return None
    match = re.match(r'^\d{1,3}', str(home_name))
    return match.group(0) if match else None

# 判斷區域並返回員工的區域狀態
def check_local(row, github_df):
    home_number = extract_home_number(row['HomeName'])
    resp_staff = row['RespStaff'] if pd.notna(row['RespStaff']) else None
    second_staff = row['2ndRespStaffName'] if pd.notna(row['2ndRespStaffName']) else None

    if home_number is None:
        return {'resp_region': '外區', 'second_region': '外區' if second_staff else None}

    matching_homes = github_df[github_df['Home'].astype(str) == str(home_number)]
    if matching_homes.empty:
        return {'resp_region': '外區', 'second_region': '外區' if second_staff else None}

    local_staff = set()
    for _, home_row in matching_homes.iterrows():
        if pd.notna(home_row['staff1']):
            local_staff.add(home_row['staff1'])
        if pd.notna(home_row['staff2']):
            local_staff.add(home_row['staff2'])

    resp_region = '本區' if resp_staff in local_staff else '外區'
    second_region = '本區' if second_staff in local_staff else '外區' if second_staff else None

    return {'resp_region': resp_region, 'second_region': second_region}

# 轉換員工名稱
def convert_name(name):
    return NAME_CONVERSION.get(name, name) if pd.notna(name) else name

# 計算員工統計（含本區總共和全部總共）
def calculate_staff_stats(df, github_df):
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        st.error(f"缺少必要欄位: {missing_columns}")
        return None

    staff_stats = {}
    staff_days = {}

    for index, row in df.iterrows():
        resp_staff = convert_name(row['RespStaff'])
        second_staff = convert_name(row['2ndRespStaffName']) if pd.notna(row['2ndRespStaffName']) else None
        service_date = row['ServiceDate']

        if pd.isna(resp_staff) or pd.isna(service_date):
            continue

        if resp_staff not in staff_stats:
            staff_stats[resp_staff] = {
                '本區單獨': 0, '本區協作': 0, '外區單獨': 0, '外區協作': 0
            }
            staff_days[resp_staff] = set()
        if second_staff and second_staff not in staff_stats:
            staff_stats[second_staff] = {
                '本區單獨': 0, '本區協作': 0, '外區單獨': 0, '外區協作': 0
            }
            staff_days[second_staff] = set()

        staff_days[resp_staff].add(service_date)
        if second_staff:
            staff_days[second_staff].add(service_date)

        regions = check_local(row, github_df)
        resp_region = regions['resp_region']
        second_region = regions['second_region']

        if not second_staff:
            if resp_region == '本區':
                staff_stats[resp_staff]['本區單獨'] += 1
            else:
                staff_stats[resp_staff]['外區單獨'] += 1
        else:
            if resp_region == '本區':
                staff_stats[resp_staff]['本區協作'] += 1
            else:
                staff_stats[resp_staff]['外區協作'] += 1
            if second_region == '本區':
                staff_stats[second_staff]['本區協作'] += 1
            else:
                staff_stats[second_staff]['外區協作'] += 1

    for staff in staff_stats:
        staff_stats[staff]['外出日數'] = len(staff_days[staff])
        staff_stats[staff]['本區總共'] = staff_stats[staff]['本區單獨'] + staff_stats[staff]['本區協作']
        staff_stats[staff]['全部總共'] = (staff_stats[staff]['本區總共'] + 
                                         staff_stats[staff]['外區單獨'] + 
                                         staff_stats[staff]['外區協作'])

    return staff_stats, staff_days

# 計算分區統計節數並返回詳細記錄（含人次和活動類型統計）
def calculate_region_stats(df, github_df):
    region_stats = {
        'Ling': {'count': 0, 'homes': set(), 'records': [], 'participants': 0, 'activity_types': {}},
        'Mike': {'count': 0, 'homes': set(), 'records': [], 'participants': 0, 'activity_types': {}},
        'Pong': {'count': 0, 'homes': set(), 'records': [], 'participants': 0, 'activity_types': {}},
        'Peppy': {'count': 0, 'homes': set(), 'records': [], 'participants': 0, 'activity_types': {}}
    }

    has_participants_column = 'NumberOfParticipant(Without Volunteer Count)' in df.columns
    has_activity_type_column = '活動類型' in df.columns

    for index, row in df.iterrows():
        home_number = extract_home_number(row['HomeName'])
        if home_number is None:
            continue

        matching_homes = github_df[github_df['Home'].astype(str) == str(home_number)]
        if matching_homes.empty:
            continue

        staff1 = matching_homes.iloc[0]['staff1']
        if pd.isna(staff1) or staff1 not in region_stats:
            continue

        region_stats[staff1]['count'] += 1
        region_stats[staff1]['homes'].add(home_number)
        record = {
            'RespStaff': row['RespStaff'],
            'ServiceDate': row['ServiceDate'],
            'HomeName': row['HomeName']
        }
        region_stats[staff1]['records'].append(record)

        if has_participants_column and pd.notna(row['NumberOfParticipant(Without Volunteer Count)']):
            try:
                participants = int(row['NumberOfParticipant(Without Volunteer Count)'])
                region_stats[staff1]['participants'] += participants
            except ValueError:
                continue

        if has_activity_type_column and pd.notna(row['活動類型']):
            activity_type = row['活動類型']
            region_stats[staff1]['activity_types'][activity_type] = region_stats[staff1]['activity_types'].get(activity_type, {'count': 0, 'dates': []})
            region_stats[staff1]['activity_types'][activity_type]['count'] += 1
            region_stats[staff1]['activity_types'][activity_type]['dates'].append(row['ServiceDate'])

    total_sessions = sum(region['count'] for region in region_stats.values())
    total_participants = sum(region['participants'] for region in region_stats.values()) if has_participants_column else None
    return region_stats, total_sessions, total_participants

# 獲取員工的詳細記錄
def get_staff_details(df, staff_name):
    solo_records = []
    collab_records = []
    solo_days = set()
    collab_days = set()

    for index, row in df.iterrows():
        resp_staff = convert_name(row['RespStaff'])
        second_staff = convert_name(row['2ndRespStaffName']) if pd.notna(row['2ndRespStaffName']) else None
        service_date = row['ServiceDate']
        home_name = row['HomeName']

        if resp_staff == staff_name and not second_staff:
            solo_records.append({'ServiceDate': service_date, 'HomeName': home_name})
            solo_days.add(service_date)
        elif resp_staff == staff_name and second_staff:
            collab_records.append({'ServiceDate': service_date, 'HomeName': home_name, 'Collaborator': second_staff})
            collab_days.add(service_date)
        elif second_staff == staff_name:
            collab_records.append({'ServiceDate': service_date, 'HomeName': home_name, 'Collaborator': resp_staff})
            collab_days.add(service_date)

    all_days = solo_days.union(collab_days)
    return {
        'solo_records': solo_records,
        'collab_records': collab_records,
        'solo_days': sorted(solo_days),
        'collab_days': sorted(collab_days),
        'all_days': sorted(all_days)
    }

# 計算院舍活動次數統計
def calculate_home_activity_stats(df):
    if 'HomeName' not in df.columns or 'ServiceDate' not in df.columns:
        st.error("缺少 'HomeName' 或 'ServiceDate' 欄位，無法計算院舍活動次數")
        return None, None

    # 按 HomeName 分組，計算每間院舍的活動次數
    home_activity_counts = df.groupby('HomeName').size()  # 目前假設 NumberOfSession 為 1，若不然可用 .sum()
    # 統計各次數的院舍數量
    home_counts = home_activity_counts.value_counts().to_dict()
    # 確保從 1 次開始，補充缺失的次數
    max_count = max(home_counts.keys(), default=0)
    home_counts = {i: home_counts.get(i, 0) for i in range(1, max_count + 1)}

    # 儲存每間院舍的活動日期
    home_details = df.groupby('HomeName')['ServiceDate'].apply(list).to_dict()

    return home_counts, home_details

# 列表頁
def list_page():
    st.title("GitHub homelist.csv 列表")
    st.write("從 GitHub 儲存庫讀取並顯示 homelist.csv 的內容。")

    df = get_github_csv_data(RAW_URL)
    if df is not None:
        st.subheader("homelist.csv 內容")
        df.index = df.index + 1  # 索引從 1 開始
        st.dataframe(df)

# 自定義樣式函數（為員工統計表設置顏色）
def style_staff_table(df):
    def row_style(row):
        if row.name == 'Ling' or row.name == 'Kayi':
            return ['background-color: #FFF5BA'] * len(row)  # 粉黃色
        elif row.name == 'Mike':
            return ['background-color: #FFE6E6'] * len(row)  # 更淺的粉紅色
        elif row.name == 'Pong' or row.name == 'Jack':
            return ['background-color: #CCFFCC'] * len(row)  # 粉綠色
        elif row.name == 'Peppy' or row.name == 'Kama':
            return ['background-color: #CCE5FF'] * len(row)  # 粉藍色
        return [''] * len(row)
    
    return df.style.apply(row_style, axis=1)

# 外出統計程式頁
def outing_stats_page():
    st.title("外出統計程式")
    st.markdown("""
    **self note:**  
    步驟1>>>首先人手核對一次CaseNumber欄位有無錯誤加入了職員姓名。  
    步驟2>>> 下載好檔案後, 用頂欄進行篩選, 在CaseName欄位剔走包含院友名的資料。複製篩好的資料到新活頁簿, 刪走原先的活頁簿。另存檔案後再上載到此頁面程式
    """)
    st.write("請上傳 CSV 或 XLSX 檔案，程式將根據 GitHub 的 homelist.csv 計算每位員工的本區與外區單獨及協作節數，並顯示分區統計節數（CSV 使用 Big5HKSCS 編碼）。")

    # 檢查是否已經有上傳的數據
    if st.session_state['uploaded_df'] is None:
        uploaded_file = st.file_uploader("選擇 CSV 或 XLSX 檔案", type=["csv", "xlsx"], key="outing_uploader")
        if uploaded_file is not None:
            st.write("檔案已上傳，名稱:", uploaded_file.name)
            uploaded_df, used_encoding = read_file(uploaded_file)
            if uploaded_df is None:
                return
            st.session_state['uploaded_df'] = uploaded_df
            st.session_state['used_encoding'] = used_encoding
    else:
        st.write("已使用之前上傳的檔案，若需更換請重新上傳。")
        uploaded_file = st.file_uploader("選擇 CSV 或 XLSX 檔案", type=["csv", "xlsx"], key="outing_uploader")
        if uploaded_file is not None:
            st.write("檔案已上傳，名稱:", uploaded_file.name)
            uploaded_df, used_encoding = read_file(uploaded_file)
            if uploaded_df is None:
                return
            st.session_state['uploaded_df'] = uploaded_df
            st.session_state['used_encoding'] = used_encoding

    uploaded_df = st.session_state['uploaded_df']
    used_encoding = st.session_state['used_encoding']

    if uploaded_df is not None:
        uploaded_df['RespStaff'] = uploaded_df['RespStaff'].apply(convert_name)
        uploaded_df['2ndRespStaffName'] = uploaded_df['2ndRespStaffName'].apply(convert_name)

        st.write(f"檔案成功解析，使用編碼: {used_encoding}")

        github_df = get_github_csv_data(RAW_URL)
        if github_df is None:
            return

        required_uploaded_cols = ['HomeName', 'RespStaff', '2ndRespStaffName', 'ServiceDate']
        required_github_cols = ['Home', 'staff1', 'staff2']
        missing_uploaded = [col for col in required_uploaded_cols if col not in uploaded_df.columns]
        missing_github = [col for col in required_github_cols if col not in github_df.columns]

        if missing_uploaded:
            st.error(f"上傳的檔案缺少必要欄位: {missing_uploaded}")
            return
        if missing_github:
            st.error(f"GitHub 的 homelist.csv 缺少必要欄位: {missing_github}")
            return

        uploaded_df[['RespRegion', 'SecondRegion']] = uploaded_df.apply(
            lambda row: pd.Series(check_local(row, github_df)), axis=1
        )

        staff_stats, staff_days = calculate_staff_stats(uploaded_df, github_df)
        if staff_stats is None:
            st.error("統計計算失敗，請檢查錯誤訊息")
            return

        region_stats, total_sessions, total_participants = calculate_region_stats(uploaded_df, github_df)

        # 計算院舍活動次數
        home_counts, home_details = calculate_home_activity_stats(uploaded_df)
        if home_counts is None:
            return

        # 並排顯示員工統計表和分區統計節數
        col1, col2 = st.columns([7, 3])

        with col1:
            st.subheader("員工外出統計表")
            stats_df = pd.DataFrame(staff_stats).T
            stats_df = stats_df[['本區單獨', '本區協作', '本區總共', '外區單獨', '外區協作', '全部總共', '外出日數']]
            stats_df.index.name = '員工'
            desired_order = ['Ling', 'Mike', 'Pong', 'Peppy', 'Kayi', 'Jack', 'Kama']
            existing_staff = [staff for staff in desired_order if staff in stats_df.index]
            stats_df = stats_df.reindex(existing_staff)
            styled_df = style_staff_table(stats_df)
            st.dataframe(styled_df, height=300)

        with col2:
            st.subheader("分區統計節數")
            region_data = {
                '分區': list(region_stats.keys()),
                '節數': [region_stats[region]['count'] for region in region_stats]
            }
            if 'NumberOfParticipant(Without Volunteer Count)' in uploaded_df.columns:
                region_data['人次'] = [region_stats[region]['participants'] for region in region_stats]
            region_df = pd.DataFrame(region_data)
            region_df.loc[len(region_df)] = ['總計', total_sessions] + ([total_participants] if '人次' in region_df.columns else [])
            region_df.index = region_df.index + 1  # 索引從 1 開始
            st.dataframe(region_df, height=300)

        # 並排顯示 ServiceStatus 和 活動類型 統計
        col1, col2 = st.columns(2)

        with col1:
            st.write("**ServiceStatus 統計：**")
            if 'ServiceStatus' in uploaded_df.columns:
                status_counts = uploaded_df['ServiceStatus'].value_counts()
                for status, count in status_counts.items():
                    st.write(f"{status}: {count} 次")
                st.write(f"總計: {status_counts.sum()} 次")
            else:
                st.write("無此欄位")

            st.write("**NumberOfSession 統計：**")
            if 'NumberOfSession' in uploaded_df.columns:
                session_counts = uploaded_df['NumberOfSession'].value_counts()
                for session, count in session_counts.items():
                    st.write(f"{session}: {count} 次")
                st.write(f"總計: {session_counts.sum()} 次")
            else:
                st.write("無此欄位")

            # 院舍活動次數統計（互動表格）
            st.write("**院舍活動次數統計：**")
            home_activity_data = [
                {'活動次數': count, '院舍數目': num_homes, '總節數': count * num_homes}
                for count, num_homes in home_counts.items()
            ]
            home_activity_df = pd.DataFrame(home_activity_data)
            home_activity_df.loc[len(home_activity_df)] = ['總計', home_activity_df['院舍數目'].sum(), home_activity_df['總節數'].sum()]
            home_activity_df.index = home_activity_df.index + 1  # 索引從 1 開始
            st.dataframe(home_activity_df, height=200)

        with col2:
            st.write("**活動類型 統計：**")
            if '活動類型' in uploaded_df.columns:
                type_counts = uploaded_df['活動類型'].value_counts().reset_index()
                type_counts.columns = ['活動類型', '次數']
                type_counts.loc[len(type_counts)] = ['總計', type_counts['次數'].sum()]
                type_counts.index = type_counts.index + 1  # 索引從 1 開始
                st.dataframe(type_counts, height=200)
            else:
                st.write("無此欄位")

        # 分區詳細統計
        st.subheader("分區詳細統計")
        region_list = ['選擇分區'] + list(region_stats.keys())
        selected_region = st.selectbox("選擇分區", region_list, index=0, key="region_select")
        
        if selected_region != '選擇分區':
            participants_text = f"，人次: {region_stats[selected_region]['participants']}" if 'NumberOfParticipant(Without Volunteer Count)' in uploaded_df.columns else ""
            st.write(f"### {selected_region} 分區（{region_stats[selected_region]['count']} 節{participants_text}）")
            homes = sorted(region_stats[selected_region]['homes'])
            st.write(f"相關院舍（staff1 = {selected_region}）：{', '.join(homes)}")
            st.write("記錄清單：")
            if region_stats[selected_region]['records']:
                records_df = pd.DataFrame(region_stats[selected_region]['records'])
                records_df['ServiceDate'] = records_df['ServiceDate'].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d'))
                records_df = records_df[['RespStaff', 'ServiceDate', 'HomeName']]
                records_df.columns = ['負責員工', '活動日期', '院舍名稱']
                records_df.index = records_df.index + 1  # 索引從 1 開始
                st.dataframe(records_df, height=300)
            else:
                st.write("無記錄")

        # 員工詳細統計
        st.subheader("員工外出詳細統計")
        staff_list = ['選擇員工'] + list(staff_stats.keys())
        selected_staff = st.selectbox("選擇員工", staff_list, index=0, key="staff_select")

        if selected_staff != '選擇員工':
            details = get_staff_details(uploaded_df, selected_staff)
            st.write(f"### {selected_staff}")
            
            st.write("**單獨記錄：**")
            if details['solo_records']:
                solo_df = pd.DataFrame(details['solo_records'])
                solo_df['ServiceDate'] = solo_df['ServiceDate'].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d'))
                solo_df.columns = ['活動日期', '院舍名稱']
                solo_df.index = solo_df.index + 1  # 索引從 1 開始
                st.dataframe(solo_df, height=200)
            else:
                st.write("無單獨記錄")

            st.write("**協作記錄：**")
            if details['collab_records']:
                collab_df = pd.DataFrame(details['collab_records'])
                collab_df['ServiceDate'] = collab_df['ServiceDate'].apply(lambda x: pd.to_datetime(x).strftime('%Y-%m-%d'))
                collab_df.columns = ['活動日期', '院舍名稱', '協作者']
                collab_df.index = collab_df.index + 1  # 索引從 1 開始
                st.dataframe(collab_df, height=200)
            else:
                st.write("無協作記錄")

            st.write("**不重複日期：**")
            solo_days_str = [pd.to_datetime(day).strftime('%Y-%m-%d') for day in details['solo_days']]
            collab_days_str = [pd.to_datetime(day).strftime('%Y-%m-%d') for day in details['collab_days']]
            all_days_str = [pd.to_datetime(day).strftime('%Y-%m-%d') for day in details['all_days']]
            st.write(f"單獨：{', '.join(solo_days_str)} → {len(details['solo_days'])} 天")
            st.write(f"協作：{', '.join(collab_days_str)} → {len(details['collab_days'])} 天")
            st.write(f"總計：{', '.join(all_days_str)} → {len(details['all_days'])} 天")

        # 院舍活動次數詳細統計（下拉清單）
        st.subheader("院舍活動次數詳細統計")
        activity_options = [f"{count} 次" for count in home_counts.keys()]
        selected_activity_count = st.selectbox("選擇活動次數", ['選擇次數'] + activity_options, index=0, key="home_activity_select")

        if selected_activity_count != '選擇次數':
            count = int(selected_activity_count.split()[0])  # 提取數字部分，例如 "1 次" -> 1
            # 過濾出符合次數的院舍
            filtered_homes = {home: dates for home, dates in home_details.items() if len(dates) == count}
            if filtered_homes:
                # 準備表格數據，移除時間部分
                home_activity_data = [
                    {'院舍名稱': home, '活動日期': ', '.join(pd.to_datetime(date).strftime('%Y-%m-%d') for date in dates)}
                    for home, dates in filtered_homes.items()
                ]
                home_activity_df = pd.DataFrame(home_activity_data)
                home_activity_df.index = home_activity_df.index + 1  # 索引從 1 開始
                st.write(f"### 活動次數為 {count} 次的院舍（共 {len(filtered_homes)} 間）")
                st.dataframe(home_activity_df, height=300)
            else:
                st.write(f"沒有活動次數為 {count} 次的院舍")

        # 活動類型詳細統計
        st.subheader("活動類型詳細統計")
        region_list = ['選擇分區'] + list(region_stats.keys())
        selected_activity_region = st.selectbox("選擇分區查看活動類型統計", region_list, index=0, key="activity_type_select")

        if selected_activity_region != '選擇分區':
            st.write(f"### {selected_activity_region} 分區活動類型統計")
            activity_types = region_stats[selected_activity_region]['activity_types']
            if activity_types:
                activity_type_data = [
                    {
                        '活動類型': activity,
                        '節數': details['count'],
                        '活動日期': ', '.join(pd.to_datetime(date).strftime('%Y-%m-%d') for date in details['dates'])
                    }
                    for activity, details in activity_types.items()
                ]
                activity_type_df = pd.DataFrame(activity_type_data)
                activity_type_df.loc[len(activity_type_df)] = ['總計', activity_type_df['節數'].sum(), '']
                activity_type_df.index = activity_type_df.index + 1  # 索引從 1 開始
                st.dataframe(activity_type_df, height=300)
            else:
                st.write("此分區無活動類型記錄")

# 統計圖頁面
def stats_chart_page():
    st.title("統計圖")
    st.write("此頁面顯示活動類型的統計圖表，並允許調整圖表大小和字體大小。")

    if st.session_state['uploaded_df'] is None:
        st.warning("請先在「外出統計程式」頁面上傳 CSV 或 XLSX 檔案以生成圖表。")
        return

    uploaded_df = st.session_state['uploaded_df']

    if '活動類型' in uploaded_df.columns:
        type_counts = uploaded_df['活動類型'].value_counts().reset_index()
        type_counts.columns = ['活動類型', '次數']
        type_counts.loc[len(type_counts)] = ['總計', type_counts['次數'].sum()]
        type_counts.index = type_counts.index + 1  # 索引從 1 開始

        if 'ServiceDate' in uploaded_df.columns:
            try:
                uploaded_df['ServiceDate'] = pd.to_datetime(uploaded_df['ServiceDate'], errors='coerce')
                year = uploaded_df['ServiceDate'].dt.year.iloc[0]
                month = uploaded_df['ServiceDate'].dt.month.iloc[0]
                title = f"{year}年{month}月 份活動內容"
            except Exception as e:
                st.warning(f"無法解析 ServiceDate 欄位：{str(e)}，使用默認標題。")
                title = "2025年1月 份活動內容"
        else:
            st.warning("上傳的檔案中無 ServiceDate 欄位，使用默認標題。")
            title = "2025年1月 份活動內容"

        # 使用 st.columns 實現並列顯示，比例為 3:7
        col1, col2 = st.columns([2, 8])

        # 左邊列：調整參數
        with col1:
            with st.expander("調整圖表參數", expanded=True):  # 默認展開
                chart_width = st.slider("圖表寬度", min_value=600, max_value=1200, value=800, step=50, help="調整圖表寬度")
                chart_height = st.slider("圖表高度", min_value=400, max_value=800, value=600, step=50, help="調整圖表高度")
                chart_font_size = st.slider("圖表字體大小（標籤和圖例）", min_value=10, max_value=30, value=16, step=1, help="調整標籤和圖例字體大小")
                center_text_size = st.slider("中心文字字體大小", min_value=10, max_value=30, value=18, step=1, help="調整中心文字（院舍數目和數字）字體大小")
                title_font_size = st.slider("標題字體大小", min_value=10, max_value=40, value=24, step=1, help="調整標題字體大小")

        # 右邊列：圓形圖
        with col2:
            st.write("**活動類型分佈圖：**")
            fig = graph.create_activity_type_donut_chart(
                type_counts, 
                title, 
                chart_width=chart_width, 
                chart_height=chart_height, 
                chart_font_size=chart_font_size, 
                center_text_size=center_text_size, 
                title_font_size=title_font_size
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("上傳的檔案中無「活動類型」欄位，無法生成圖表。")

# 主程式：頁面切換
def main():
    st.sidebar.title("頁面導航")
    page = st.sidebar.selectbox("選擇頁面", ["外出統計程式", "列表頁", "統計圖"], index=0)

    if page == "外出統計程式":
        outing_stats_page()
    elif page == "列表頁":
        list_page()
    elif page == "統計圖":
        stats_chart_page()

if __name__ == "__main__":
    main()
