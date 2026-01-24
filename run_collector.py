# run_collection.py
import os
import time
import pandas as pd
from kis_api import KISApi

def run():
    # 1. API 연결
    api = KISApi()
    
    # 저장 폴더 확인
    if not os.path.exists("data/raw"):
        os.makedirs("data/raw")

    print("🚀 데이터 수집기 가동 (Top 100 모드)")

    # 2. 시가총액 상위 100개 리스트 확보
    top_100_symbols = api.get_top_100()
    
    if not top_100_symbols:
        print("❌ 종목 리스트를 가져오지 못했습니다. 프로그램을 종료합니다.")
        return

    print(f"✅ 총 {len(top_100_symbols)}개 종목의 데이터를 수집합니다.")
    
    # 3. 각 종목별 데이터 수집 (Loop)
    for idx, symbol in enumerate(top_100_symbols):
        print(f"[{idx+1}/{len(top_100_symbols)}] {symbol} 데이터 수집 중...", end=" ")
        
        # 과거 데이터 요청 (분봉)
        df = api.fetch_ohlcv(symbol, timeframe='3m')
        
        if df is not None and not df.empty:
            # 필요한 컬럼만 선택 (API 응답 키값 기준)
            # stck_prpr:현재가, stck_oprc:시가, stck_hgpr:고가, stck_lwpr:저가, cntg_vol:체결량
            df_save = df[['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'cntg_vol']]
            
            # CSV 저장
            df_save.to_csv(f"data/raw/{symbol}_3min.csv", index=False)
            print("완료")
        else:
            print("실패 (데이터 없음)")
        
        # [중요] API 호출 제한 방지 (초당 2회 제한 준수)
        time.sleep(0.5)

    print("\n🎉 모든 데이터 수집이 완료되었습니다!")
    print("이제 'train.py'를 실행하여 학습을 시작하세요.")

if __name__ == "__main__":
    run()