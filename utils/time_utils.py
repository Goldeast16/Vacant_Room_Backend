from datetime import datetime

def calculate_minutes_diff(start: str, end: str) -> int:
    s = datetime.strptime(start, "%H:%M")
    e = datetime.strptime(end, "%H:%M")
    delta = e - s
    return int(delta.total_seconds() // 60)

def format_minutes_to_string(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    if hours and mins:
        return f"{hours}시간 {mins}분"
    elif hours:
        return f"{hours}시간"
    else:
        return f"{mins}분"
