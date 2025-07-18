import pandas as pd
import os
import re
import json
from collections import defaultdict

def convert_period_to_time(period_num: int) -> str:
    # 0교시: 8시 시작, 그 이후는 9시부터 시작
    base_hour = 8 if period_num == 0 else 9 + (period_num - 1)
    start = f"{base_hour:02d}:00"
    end = f"{base_hour + 1:02d}:00"
    return f"{start}~{end}"

def parse_schedule(schedule_str: str):
    if pd.isna(schedule_str):
        return None, None, None

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
    building = classroom = None
    if room_part:
        match_room = re.match(r"(\d+관).*?(\d+-?\d*호)", room_part)
        if match_room:
            building = match_room.group(1)
            classroom = match_room.group(2)

    return " / ".join(time_parts), building, classroom

def split_time_info(time_str):
    if pd.isna(time_str):
        return None, None

    days, times = [], []

    # 예: 월(10:30~11:45)
    parts = [p.strip() for p in time_str.split('/')]

    for part in parts:
        match = re.match(r"([월화수목금토일])\((\d{2}:\d{2}~\d{2}:\d{2})\)", part)
        if match:
            days.append(match.group(1))
            times.append(match.group(2))

    return days, times
def process_excel_file(filepath: str) -> list[dict]:
    df = pd.read_excel(filepath, engine="openpyxl")
    df = df[["과목번호-분반", "과목명", "담당교수", "폐강", "강의시간"]]
    df = df[df["폐강"].isna()].drop(columns=["폐강"])

    df["담당교수"] = df["담당교수"].fillna("미정")

    df[["강의시간_24시", "건물번호", "강의실"]] = df["강의시간"].apply(
        lambda x: pd.Series(parse_schedule(x))
    )

    df[["강의요일", "강의시간_리스트"]] = df["강의시간_24시"].apply(
        lambda x: pd.Series(split_time_info(x))
    )

    df = df.drop(columns=["강의시간", "강의시간_24시"])

    df["temp"] = df.apply(lambda row: list(zip(row["강의요일"], row["강의시간_리스트"])), axis=1)
    df = df.explode("temp")
    df = df[df["temp"].apply(lambda x: isinstance(x, tuple) and len(x) == 2)]

    df[["요일", "시간"]] = pd.DataFrame(df["temp"].tolist(), index=df.index)
    df = df.drop(columns=["temp", "강의요일", "강의시간_리스트"])

    df[["start_time", "end_time"]] = df["시간"].str.split("~", expand=True)
    df = df.drop(columns=["시간"])

    df = df.rename(columns={
        "건물번호": "building",
        "강의실": "room",
        "요일": "day",
        "과목번호-분반": "course_id",
        "과목명": "course_name",
        "담당교수": "professor"
    })

    df = df[["building", "room", "day", "start_time", "end_time", "course_id", "course_name", "professor"]]

    df["building"] = df["building"].apply(lambda x: re.search(r"\d+", str(x)).group() if pd.notna(x) else None)
    df["room"] = df["room"].apply(lambda x: re.search(r"\d+(?:-\d+)?", str(x)).group() if pd.notna(x) else None)
    df = df.dropna(subset=["building", "room"])
    df["building"] = df["building"].astype(int)

    day_map = {
        "월": "monday", "화": "tuesday", "수": "wednesday",
        "목": "thursday", "금": "friday", "토": "saturday", "일": "sunday"
    }
    df["day"] = df["day"].map(day_map)

    data = df.to_dict(orient="records")
    for row in data:
        row["start_time"] = row["start_time"][:5]
        row["end_time"] = row["end_time"][:5]

    # 중복 제거 기준: 핵심 필드들이 모두 같은 경우
    df = df.drop_duplicates(subset=[
        "building", "room", "day", "start_time", "end_time", "course_id"
    ])

    return data

def convert_all_excels(raw_dir: str, save_dir: str):
    os.makedirs(save_dir, exist_ok=True)
    building_data = defaultdict(list)  # building 번호 → 리스트 모음

    for filename in os.listdir(raw_dir):
        if filename.endswith(".xlsx"):
            file_path = os.path.join(raw_dir, filename)
            lecture_list = process_excel_file(file_path)
            for row in lecture_list:
                building_data[row["building"]].append(row)

    # 각 건물별로 저장
    for building, records in building_data.items():
        save_name = f"{building}_lectures.json"
        save_path = os.path.join(save_dir, save_name)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"{building}번 건물 → {save_name} 저장 완료")

# 실행 예시
if __name__ == "__main__":
    convert_all_excels("raw_data", "converted_data")