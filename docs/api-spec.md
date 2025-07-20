<7.20 수정>
### 빈 강의실 조회 API

**Endpoint**: GET /api/rooms

**Query Parameters**:

- building (필수): 건물 번호 (예: "310")
- hour (필수): 현재 시각 (예: 13)
- minute (필수): 현재 분 (예: 00)
- weekday (필수): 요일 (예: "수")
- floor (선택): 층 (예: 6, 선택적)

```json
[
  {
    "building": "310",
    "floor": 6,
    "room_number": "601",
    "status": "empty",
    "current_lecture": null,
    "next_lecture": null,
    "soon_message": null,
    "available_minutes": 1440
  },
  {
    "building": "310",
    "floor": 6,
    "room_number": "603",
    "status": "soon",
    "current_lecture": null,
    "next_lecture": {
      "course": "의생명을 위한 멀티모달 AI 개론",
      "start": "14:00",
      "end": "16:00"
    },
    "soon_message": "60분 뒤 의생명을 위한 멀티모달 AI 개론 수업이 시작됩니다.",
    "available_minutes": 60
  }
]
```

**요청사항**

- status는 현재 시간 기준으로 자동 계산:
    - "in_use": 지금 수업 중
    - "soon": 1시간 이내 수업 예정
    - "empty": 수업 없음
- current_lecture: 현재 수업 정보 (현재 수업이 없으면 null)
- next_lecture: 다음 수업 시작 시간 (없으면 null)
- 수업 시간은 "HH:mm" 포맷 사용
- 시간 필터는 10분 단위 (예: 13:00, 13:10, 13:20...)
- 요청된 building, floor, hour, minute 를 기준으로 빈 강의실 목록 반환

빈 강의실 조회 API에서는 status, current_lecture, next_lecture 정보를 포함한 

강의실 상태를 실시간으로 계산하여 제공할 수 있도록 구성

### 강의실 시간표 조회 API

**Endpoint**: GET /api/room-timetable

**Query Parameters**:

- building: 건물 번호 (예: "310")
- room_number: 강의실 번호 (예: "601")
- weekday: 조회할 요일 (예: "월", "화", "수", "목", "금")

```json
[
  {
    "course": "인공지능설계 (영어A강의)(전공자만)",
    "start": "13:00",
    "end": "15:00"
  }
]
```

**요청사항**

- 수업 시간은 "HH:mm” 포맷 사용
- 날짜 기준으로 해당 강의실의 하루 전체 시간표 반환
- 모든 시간 필터는 10분 단위로 처리 (예: "09:00", "09:10", "09:20"...)

강의실 시간표 조회 API는 하루 전체 시간표를 제공하고, 프론트엔드가 실시간 상태를 계산하여 화면에 표시할 수 있도록 데이터 구조가 구성되어야 함

### 강의실 층 정보 조회 API

**Endpoint**: GET /api/floors

**Query Parameters**:

- building (string, 필수): 건물 번호 (예: "310")

```json
[
  4,
  5,
  6
]
```

**요청사항**

- 해당 건물에 있는 층 번호 목록을 반환. 예시에서는 "310" 건물에 4층, 5층, 6층이 있다는 정보가 제공.

building(건물 번호)을 파라미터로 받아 해당 건물에 존재하는 층 번호들을 배열로 반환해야함.

### **주요 수정 사항**

- **빈 강의실 조회 API에서 추가된 필드**
    
    **soon_message, available_minutes, current_lecture, next_lecture 추가**
    
    1. **soon_message :** 1시간 이내에 시작하는 수업에 대한 메시지 
        
        (예: "60분 뒤 알고리즘 수업이 시작됩니다.")
        
    2. **available_minutes :** 빈 강의실이 남은 시간 (분 단위, 수업이 없는 경우는 1440분 = 하루 전체)
    3. **current_lecture :** 현재 진행 중인 수업 (없으면 null)
    4. **next_lecture :** 다음 예정된 수업 (없으면 null)
- **status 계산 방식 변경**
    
     in_use: 현재 수업 중인 강의실
    
    soon: 1시간 이내에 수업이 예정된 강의실
    
    empty: 수업이 없는 강의실
    
- **강의실 시간표 조회 API에서 시간 필터 변경**

시간 필터는 10분 단위로 처리 (예: "09:00", "09:10", "09:20" 등)

- **건물 번호를 기준으로 해당 건물의 층 번호 목록을 반환하는 API 추가**
    
    강의실 층 정보 조회 API 추가
    
    (예: "310" 건물에 4층, 5층, 6층이 있다고 반환)
  
<7.18>
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
