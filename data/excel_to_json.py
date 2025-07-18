import pandas as pd
import os
import re
import json

def convert_period_to_time(period_num: int) -> str:
    # 0교시: 8시 시작, 그 이후는 9시부터 시작
    base_hour = 8 if period_num == 0 else 9 + (period_num - 1)
    start = f"{base_hour:02d}:00"
    end = f"{base_hour + 1:02d}:00"
    return f"{start}~{end}"

def parse_schedule(schedule_str: str):
    if pd.isna(schedule_str):
        return None, None, None

    # 시간 정보 추출

    # 예: '월10 / 310관 802호' 또는 '월(10:30~11:45) / 수10 / 303관 802호'
    parts = schedule_str.split('/')
    time_parts = []
    room_part = None

    for part in parts:
        part = part.strip()

        # 교시 형식 예: 월0, 수3 등
        match_period = re.match(r"([월화수목금토일])(\d+)", part)
        if match_period:
            day = match_period.group(1)
            period = int(match_period.group(2))
            time_range = convert_period_to_time(period)
            time_parts.append(f"{day}({time_range})")
            continue

        # 이미 시간으로 되어 있으면 그대로 추가
        match_time = re.match(r"([월화수목금토일])\(.+\)", part)
        if match_time:
            time_parts.append(part)
            continue

        # 강의실 정보로 간주
        if re.search(r"\d+관.*\d+호", part):
            room_part = part

    # 건물번호, 강의실 분리
    building = None
    classroom = None
    if room_part:
        match_room = re.match(r"(\d+관).*?(\d+-?\d*호)", room_part)
        if match_room:
            building = match_room.group(1)
            classroom = match_room.group(2)

    return " / ".join(time_parts), building, classroom

def split_time_info(time_str):
    if pd.isna(time_str):
        return None, None

    days = []
    times = []

    # 예: 월(10:30~11:45)
    parts = [p.strip() for p in time_str.split('/')]

    for part in parts:
        match = re.match(r"([월화수목금토일])\((\d{2}:\d{2}~\d{2}:\d{2})\)", part)
        if match:
            days.append(match.group(1))
            times.append(match.group(2))

    return days, times

# 엑셀 파일 경로
excel_path = "raw_data/25_2_department_of_economics.xlsx"

# 엑셀 로드 (첫 시트 기준)
excel_df = pd.read_excel(excel_path, engine="openpyxl")

# 1. 과목번호, 과목명, 담당교수, 폐강, 강의시간만 남기고 제거
columns_to_keep = ["과목번호-분반", "과목명", "담당교수", "폐강", "강의시간"]
excel_df = excel_df[columns_to_keep]

# 1. 폐강 열이 NaN이 아닌 행 제거
excel_df = excel_df[excel_df["폐강"].isna()]

# 2. 폐강 열 제거
excel_df = excel_df.drop(columns=["폐강"])

# 강의시간, 건물번호, 강의실 파싱해서 새 컬럼으로 추가
excel_df[["강의시간_24시", "건물번호", "강의실"]] = excel_df["강의시간"].apply(
    lambda x: pd.Series(parse_schedule(x))
)

excel_df[["강의요일", "강의시간_리스트"]] = excel_df["강의시간_24시"].apply(
    lambda x: pd.Series(split_time_info(x))
)

excel_df = excel_df.drop(columns=["강의시간", "강의시간_24시"])

# zip 요일과 시간 리스트 → 튜플 목록
excel_df["temp"] = excel_df.apply(
    lambda row: list(zip(row["강의요일"], row["강의시간_리스트"])), axis=1
)

# explode
df_exploded = excel_df.explode("temp")

# 튜플만 남기기
df_exploded = df_exploded[df_exploded["temp"].apply(lambda x: isinstance(x, tuple) and len(x) == 2)]

# 튜플 분리
df_exploded[["요일", "시간"]] = pd.DataFrame(df_exploded["temp"].tolist(), index=df_exploded.index)
df_exploded = df_exploded.drop(columns=["temp", "강의요일", "강의시간_리스트"])

df_exploded[["시작시간", "종료시간"]] = df_exploded["시간"].str.split("~", expand=True)
df_exploded = df_exploded.drop(columns=["시간"])

df_exploded = df_exploded.rename(columns={
    "건물번호": "building",
    "강의실": "room",
    "요일": "day",
    "시작시간": "start_time",
    "종료시간": "end_time",
    "과목번호-분반": "course_id",
    "과목명": "course_name",
    "담당교수": "professor"
})

df_exploded = df_exploded[
    ["building", "room", "day", "start_time", "end_time", "course_id", "course_name", "professor"]
]

# building에서 숫자만 추출 (예: "310관" → "310")
df_exploded["building"] = df_exploded["building"].apply(
    lambda x: re.search(r"\d+", str(x)).group() if pd.notna(x) else None
)

# room에서도 숫자만 추출 (예: "415호" 또는 "802-1호" → "415", "802-1")
df_exploded["room"] = df_exploded["room"].apply(
    lambda x: re.search(r"\d+(?:-\d+)?", str(x)).group() if pd.notna(x) else None
)

day_map = {
    "월": "monday",
    "화": "tuesday",
    "수": "wednesday",
    "목": "thursday",
    "금": "friday",
    "토": "saturday",
    "일": "sunday"
}

df_exploded["day"] = df_exploded["day"].map(day_map)

df_exploded = df_exploded.dropna(subset=["building", "room"])

df_exploded["building"] = df_exploded["building"].astype(int)

json_data = df_exploded.to_dict(orient="records")

save_dir = "converted_data"
os.makedirs(save_dir, exist_ok=True)

import json

save_path = os.path.join(save_dir, "room_schedule.json")

with open(save_path, "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

print(f"✅ JSON 저장 완료: {save_path}")
