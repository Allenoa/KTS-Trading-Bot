# config.py
import torch

# 1. 한국투자증권 API 설정 (본인 정보 입력 필수)
# 모의 투자 계좌
APP_KEY = "PSelPj8EY6BEzVJTMVHKCnALFECnYkxNpDdv"
APP_SECRET = "0wTdQPux2UU5gNnIRHImdm+0xar6IJ++bfvesPX9Lvv2uhY88XYIhHsExTo4eoY77YcwkNiCoz7wZrP1Jk7Kmf1RasEGAzDWDIG0jK/xuyJWCE5LVmh1AGutubP53OVs6P/4yCR3SWXgFoKafm3M9j53noRTg249gXFWCvEDVKSJVUl9vYU="
ACC_NO = "50159792" # 예: "12345678"

# # 실전 투자 계좌
# APP_KEY = "PSbl4nQdC5x4eu3qMZdyxfPiVvJElnCkb14s"
# APP_SECRET = "D9LYAbl+Htv78tGwHgaNAUt9sjP4Q7WhdLyz82hUVzTYQ90guwjVZTCUy6VV+sWNjrasAHMW7LkQrIVPtuf4pxJAL6xq8eM3H3NvOraXe5eKzHEJQqLcL+YjUmkEzDQ+HTm6FQvlRSbPCUF+Wp5LqJ2ea49MgS6FMJhNO+q9LeHT7YA1FBc="
# ACC_NO = "43783489" # 예: "12345678"

# 실전투자 URL (모의투자는 'https://openapivts.koreainvestment.com:29443')
# URL_BASE = "https://openapi.koreainvestment.com:9443"
URL_BASE = "https://openapivts.koreainvestment.com:29443"

# 2. 하드웨어 설정 (RTX 4060 활용)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 3. 전략 설정
TARGET_COUNT = 100
WINDOW_SIZE = 30             # AI가 학습할 과거 데이터 길이 (3분봉 30개 = 90분)
DYNAMIC_RATIO = 0.5          # 공격/방어 모드 전환 기준 (잔고의 50%)
STOP_LOSS_RATE = -0.02       # 손절 라인 (-2%)
TAKE_PROFIT_RATE = 0.04      # 익절 라인 (+4%)

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1460053535864393769/ym6mTR6yATneG_NLEmgli0zKhXnzdV7CZ9G5gs_SUF5Ds9XCFy80OTr8_Qj39dFagWbM"