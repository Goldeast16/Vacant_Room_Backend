from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json

def insert_building_jsons_to_mongo(json_dir: str, collection_name: str):
    load_dotenv()
    mongo_uri = os.getenv("MONGODB_URI")

    if not mongo_uri:
        raise ValueError("MONGODB_URI가 .env에 정의되어 있지 않습니다.")

    # DB 이름이 URI에 포함된 경우 → get_default_database() 사용
    client = MongoClient(mongo_uri)
    db = client.get_default_database()
    collection = db[collection_name]

    # ✅ 기존 데이터 전체 삭제
    collection.delete_many({})
    print(f"⚠️ 기존 {collection_name} 컬렉션 데이터 전체 삭제 완료")

    inserted_count = 0
    for filename in os.listdir(json_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(json_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    collection.insert_many(data)
                    inserted_count += len(data)
                    print(f"✅ {filename} → {len(data)}개 삽입 완료")

    print(f"\n🎉 총 {inserted_count}개 강의가 {collection_name} 컬렉션에 저장되었습니다.")

# 실행 예시
if __name__ == "__main__":
    insert_building_jsons_to_mongo(
        json_dir="converted_data",
        collection_name="2025_2_lectures"
    )
