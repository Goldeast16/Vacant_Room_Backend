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

    # 예: 월13:30~14:45, 수13:30~14:45 → 월13:30~14:45 / 수13:30~14:45 로 분리
    schedule_str = re.sub(r"([월화수목금토일]\d{1,2}:\d{2}~\d{1,2}:\d{2}),\s*", r"\1 / ", schedule_str)

    # 예: 화0,1,2, 목0,1,2 → 화0,1,2 / 목0,1,2 로 분리
    schedule_str = re.sub(r"([월화수목금토일][\d,]+),\s*(?=[월화수목금토일])", r"\1 / ", schedule_str)

    parts = [p.strip() for p in schedule_str.split('/') if p.strip()]
    schedule_info = []
    room_candidates = []

    for part in parts:
        # ex: 화(15:00~16:15)
        match_paren_time = re.match(r"([월화수목금토일])\((\d{2}:\d{2})~(\d{2}:\d{2})\)", part)
        if match_paren_time:
            schedule_info.append({
                "day": match_paren_time.group(1),
                "start_time": match_paren_time.group(2),
                "end_time": match_paren_time.group(3)
            })
            continue

        # ex: 월13:30~14:45 → 괄호 없이 시간 표현된 경우
        match_plain_time = re.match(r"([월화수목금토일])(\d{1,2}:\d{2})~(\d{1,2}:\d{2})", part)
        if match_plain_time:
            schedule_info.append({
                "day": match_plain_time.group(1),
                "start_time": match_plain_time.group(2),
                "end_time": match_plain_time.group(3)
            })
            continue

        # ex: 목3,4 — 교시 기반 시간 처리
        match_day_periods = re.match(r"([월화수목금토일])([\d,]*)", part)
        if match_day_periods:
            day = match_day_periods.group(1)
            period_str = match_day_periods.group(2)

            try:
                periods = [int(p.strip()) for p in period_str.split(',') if p.strip().isdigit()]
                if periods:
                    periods.sort()
                    start = convert_period_to_time(periods[0]).split("~")[0]
                    end = convert_period_to_time(periods[-1]).split("~")[1]
                    schedule_info.append({
                        "day": day,
                        "start_time": start,
                        "end_time": end
                    })
            except ValueError:
                continue
            continue

        # 강의실: 208관 B310호
        match_room_full = re.search(r"(\d+)관.*?(B?\d+-?\d*)호", part)
        match_room_partial = re.match(r"(B?\d+-?\d*)호", part)

        if match_room_full:
            building = match_room_full.group(1)
            room = match_room_full.group(2)
            room_candidates.append((building, room))
        elif match_room_partial:
            if room_candidates:
                building = room_candidates[-1][0]
                room = match_room_partial.group(1)
                room_candidates.append((building, room))

    # 강의실 1개면 모든 시간에 공유
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

    for f in os.listdir(save_dir):
        file_path = os.path.join(save_dir, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

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

if __name__ == "__main__":
    convert_all_excels("raw_data", "converted_data")
