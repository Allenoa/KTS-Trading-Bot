# test_price.py
from kis_api import KISApi
from config import URL_BASE

def test_current_price():
    print("🏥 시세 조회 권한 정밀 진단 중...")
    
    api = KISApi()
    
    # 삼성전자(005930) 현재가 조회 시도
    # TR ID: FHKST01010100 (주식 현재가 시세)
    price = api.get_current_price("005930")
    
    print(f"\n📊 [결과 진단]")
    if price > 0:
        print(f"✅ 현재가 조회 성공: {price}원")
        print("-> 결론: 시세 조회 권한은 있습니다. 차트 요청 파라미터가 문제일 수 있습니다.")
    else:
        print("❌ 현재가 조회 실패 (0원 반환)")
        print("-> 결론: '시세(Quotations)' 권한 자체가 없습니다.")
        print("   1. API Key 발급 후 1시간이 안 지났거나")
        print("   2. API 신청 시 '시세 조회' 옵션이 빠졌거나")
        print("   3. 실전 계좌에 '시세 이용 신청'이 안 되어 있을 수 있습니다.")

if __name__ == "__main__":
    test_current_price()