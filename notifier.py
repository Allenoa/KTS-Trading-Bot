# notifier.py
import requests
import json
from datetime import datetime
from config import DISCORD_WEBHOOK_URL

def send_message(title, description, color=0x00ff00):
    """
    디스코드 채널로 메시지 전송 (시간 오류 수정 버전)
    """
    if not DISCORD_WEBHOOK_URL:
        # URL이 없으면 조용히 리턴 (에러 로그 출력 X)
        return

    # 현재 시간을 "2023-10-25 09:30:00" 같은 문자열로 예쁘게 만듭니다.
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            # [수정] timestamp 필드를 삭제하여 디스코드의 자동 변환을 막습니다.
            # 대신 footer(꼬리말)에 시간을 직접 적습니다.
            "footer": {
                "text": f"알림 시간: {now_str}" 
            }
        }]
    }

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL, 
            data=json.dumps(data), 
            headers={"Content-Type": "application/json"}
        )
        if response.status_code != 204:
            print(f"⚠️ 디스코드 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"⚠️ 알림 전송 중 에러 발생: {e}")