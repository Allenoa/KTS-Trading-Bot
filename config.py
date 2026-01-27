# config.py
import os
from dotenv import load_dotenv
import torch

load_dotenv()

# 1. 한국투자증권 API 설정 (본인 정보 입력 필수)
# 모의 투자 계좌
APP_KEY = os.getenv("KIS_DEV_APP_KEY")
APP_SECRET = os.getenv("KIS_DEV_APP_SECRET")
ACC_NO = os.getenv("KIS_DEV_ACC_NO")

# # 실전 투자 계좌
# APP_KEY = os.getenv("KIS_LIVE_APP_KEY")
# APP_SECRET = os.getenv("KIS_LIVE_APP_SECRET")
# ACC_NO = os.getenv("KIS_LIVE_ACC_NO")

# 실전투자 URL (모의투자는 'https://openapivts.koreainvestment.com:29443')
# URL_BASE = "https://openapi.koreainvestment.com:9443"
URL_BASE = "https://openapivts.koreainvestment.com:29443"

if not APP_KEY or not APP_SECRET:
    print("❌ [오류] .env 파일에서 APP_KEY 또는 APP_SECRET을 찾을 수 없습니다.")
    print("   -> .env 파일이 있는지, 변수명이 정확한지 확인해주세요.")

# 2. 하드웨어 설정 (RTX 4060 활용)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 3. 전략 설정
TARGET_COUNT = 100
WINDOW_SIZE = 30             # AI가 학습할 과거 데이터 길이 (3분봉 30개 = 90분)
DYNAMIC_RATIO = 0.5          # 공격/방어 모드 전환 기준 (잔고의 50%)
STOP_LOSS_RATE = -0.02       # 손절 라인 (-2%)
TAKE_PROFIT_RATE = 0.04      # 익절 라인 (+4%)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")