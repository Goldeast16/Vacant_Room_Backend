1. 빈 강의실 조회 API

1. Endpoint: GET /api/rooms
2. Query Parameters:
    
    building (예: "310")
    
    floor (예: 4)
    
    hour (예: 13)
    
    minute (예: 30)
    
3. example

```json
[
  {
    "building": "310",
    "floor": 4,
    "room_number": "410",
    "status": "in_use",  // 또는 "soon", "empty"
    "current_lecture": {
      "course": "자료구조",
      "start": "13:00",
      "end": "14:15"
    },
    "next_lecture": "15:00"
  },
  {
    "building": "310",
    "floor": 4,
    "room_number": "412",
    "status": "empty",
    "current_lecture": null,
    "next_lecture": null}
]
```

요청사항

status는 현재 시간 기준 자동 계산:

in_use: 지금 수업 중

soon: 1시간 이내 수업 예정

empty: 수업 없음

current_lecture: 현재 수업 정보 (없으면 null)

next_lecture: 다음 수업 시작 시간 (없으면 null)

수업 시간은 "HH:mm" 포맷

시간 필터는 10분 단위 (예: 13:00, 13:10, 13:20...)

2. 강의실 시간표 조회 API

1. Endpoint: GET /api/room-timetable
2. Query Parameters:
    
    building (예: "310")
    
    room_number (예: "410")
    
    date (예: "2025-07-18")
    
3. example

```json
[
  { "start": "09:00", "end": "10:15", "course": "자료구조" },
  { "start": "14:00", "end": "15:15", "course": "알고리즘" }
]
```

요청사항

수업 시간은 "HH:mm" 포맷

날짜 기준 해당 강의실의 하루 전체 시간표

***

      모든 시간 필터는 10분 단위 기준

빈 강의실 조회 시, status, current_lecture, next_lecture 포함

하루 시간표 기반으로 프론트가 실시간 상태 계산 및 표시 가능하도록 데이터 구성
