import pandas as pd
import os
import re
import json
from collections import defaultdict

def convert_period_to_time(period_num: int) -> str:
    base_hour = 8 if period_num == 0 else 9 + (period_num - 1)
    start = f"{base_hour:02d}:00"
    end = f"{base_hour + 1:02d}:00"
    return f"{start}~{end}"

def parse_schedule(schedule_str: str):
    if pd.isna(schedule_str):
        return None

    parts = schedule_str.split('/')
    schedule_info = []
    room_candidates = []

    for part in parts:
        part = part.strip()

        # ex: 화(15:00~16:15)
        match_time = re.match(r"([월화수목금토일])\((\d{2}:\d{2})~(\d{2}:\d{2})\)", part)
        if match_time:
            day = match_time.group(1)
            start = match_time.group(2)
            end = match_time.group(3)
            schedule_info.append({
                "day": day,
                "start_time": start,
                "end_time": end
            })
            continue

        # ex: 목3,4
        match_multiple = re.match(r"([월화수목금토일])([\d,]+)", part)
        if match_multiple:
            day = match_multiple.group(1)
            periods = [int(p) for p in match_multiple.group(2).split(',')]
            periods.sort()
            start = convert_period_to_time(periods[0]).split("~")[0]
            end = convert_period_to_time(periods[-1]).split("~")[1]
            schedule_info.append({
                "day": day,
                "start_time": start,
                "end_time": end
            })
            continue

        # 강의실: B310관, 208관 등
        match_room = re.search(r"(\d+)관.*?(B?\d+-?\d*)호", part)
        if match_room:
            building = match_room.group(1)
            room = match_room.group(2)
            room_candidates.append((building, room))

    # 강의실 수가 1개면 전체에 공유
    share_rooms = len(room_candidates) == 1

    results = []
    for i, item in enumerate(schedule_info):
        if share_rooms:
            building, room = room_candidates[0]
        elif i < len(room_candidates):
            building, room = room_candidates[i]
        else:
            building, room = None, None

        results.append({
            "day": item["day"],
            "start_time": item["start_time"],
            "end_time": item["end_time"],
            "building": building,
            "room": room
        })

    return results



def process_excel_file(filepath: str) -> list[dict]:
    df = pd.read_excel(filepath, engine="openpyxl")
    df = df[["과목번호-분반", "과목명", "담당교수", "폐강", "강의시간"]]
    df = df[df["폐강"].isna()].drop(columns=["폐강"])
    df["담당교수"] = df["담당교수"].fillna("미정")

    parsed_rows = []
    for _, row in df.iterrows():
        parsed = parse_schedule(row["강의시간"])
        if parsed:
            for p in parsed:
                parsed_rows.append({
                    "course_id": row["과목번호-분반"],
                    "course_name": row["과목명"],
                    "professor": row["담당교수"],
                    **p
                })

    df = pd.DataFrame(parsed_rows)
    df = df.dropna(subset=["building", "room"])
    df["building"] = df["building"].astype(int)

    day_map = {
        "월": "monday", "화": "tuesday", "수": "wednesday",
        "목": "thursday", "금": "friday", "토": "saturday", "일": "sunday"
    }
    df["day"] = df["day"].map(day_map)

    df = df[[
        "building", "room", "day", "start_time", "end_time",
        "course_id", "course_name", "professor"
    ]]
    df = df.drop_duplicates(subset=[
        "building", "room", "day", "start_time", "end_time", "course_id"
    ])

    return df.to_dict(orient="records")

def convert_all_excels(raw_dir: str, save_dir: str):
    os.makedirs(save_dir, exist_ok=True)
    building_data = defaultdict(list)

    for filename in os.listdir(raw_dir):
        if filename.endswith(".xlsx"):
            file_path = os.path.join(raw_dir, filename)
            lecture_list = process_excel_file(file_path)
            for row in lecture_list:
                building_data[row["building"]].append(row)

    for building, records in building_data.items():
        save_name = f"{building}_lectures.json"
        save_path = os.path.join(save_dir, save_name)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"{building}번 건물 → {save_name} 저장 완료")

# 예시 실행 코드
if __name__ == "__main__":
    convert_all_excels("raw_test", "converted_data")
