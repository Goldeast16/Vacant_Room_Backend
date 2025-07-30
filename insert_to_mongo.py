import pandas as pd
from pymongo import MongoClient

excel_path = "lecture_schedule2025_3.xlsx"

# 엑셀 파일 읽기
df = pd.read_excel(excel_path)

grouped = {}
for _, row in df.iterrows():
    key = (row["building"], row["floor"], row["room_number"])

    # floor 값을 그대로 사용 (문자와 숫자가 결합된 형태로 그대로 저장)
    floor = str(row["floor"])  # floor 값을 그대로 사용

    if key not in grouped:
        grouped[key] = {}
    if row["weekday"] not in grouped[key]:
        grouped[key][row["weekday"]] = []
    grouped[key][row["weekday"]].append({
        "course": row["course"],
        "start": row["start"],
        "end": row["end"]
    })

# MongoDB 연결
client = MongoClient("mongodb://localhost:27017")
db = client["lecture_db"]
collection = db["rooms3"]

# 기존 데이터 삭제
collection.delete_many({})

documents = []
for (building, floor, room_number), lectures_by_day in grouped.items():
    documents.append({
        "building": str(building),
        "floor": floor,  # 'B3'와 같은 형태로 floor 값을 그대로 저장
        "room_number": str(room_number),
        "lectures_by_day": lectures_by_day
    })

# 문서 삽입
collection.insert_many(documents)

print(f"{len(documents)}개의 강의실 데이터가 MongoDB에 삽입되었습니다.")