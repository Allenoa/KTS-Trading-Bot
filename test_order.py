# test_order.py
from kis_api import KISApi

def test():
    api = KISApi()
    
    # 1. 삼성전자(005930) 1주 매수 테스트
    print("--- 매수 테스트 시작 ---")
    api.buy_market_order("005930", qty=1)
    
    # 잠시 대기 (체결 시간 고려)
    import time
    time.sleep(3)
    
    # 2. 1주 매도 테스트 (원상복구)
    print("--- 매도 테스트 시작 ---")
    api.sell_market_order("005930", qty=1)

if __name__ == "__main__":
    test()