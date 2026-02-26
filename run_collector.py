# run_collector.py
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

    print("🚀 데이터 수집기 가동 (Top 100 + 수동 우량주)")

    # 2. 종목 리스트 확보 (API 실패 시 수동 리스트 자동 사용됨)
    # kis_api.py에서 이미 안전장치를 해뒀으므로 그냥 호출하면 됩니다.
    target_symbols = api.get_top_100()
    
    if not target_symbols:
        print("❌ 종목 리스트를 가져오지 못했습니다. 프로그램을 종료합니다.")
        return

    print(f"✅ 총 {len(target_symbols)}개 종목의 데이터를 수집합니다.")
    
    # 3. 각 종목별 데이터 수집 (Loop)
    for idx, symbol in enumerate(target_symbols):
        print(f"[{idx+1}/{len(target_symbols)}] {symbol} 데이터 수집 중...", end=" ")
        
        # [핵심 변경] count=500
        # 보조지표 계산(RSI 14일, 이동평균 20일)을 위해 데이터가 넉넉해야 합니다.
        # 너무 짧으면 train.py에서 전처리하다가 다 지워집니다.
        df = api.fetch_ohlcv(symbol, timeframe='3m', count=500)
        
        if df is not None and not df.empty:
            # 필요한 기본 컬럼 선택 (API 응답 키값 기준)
            df_save = df[['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'cntg_vol']]
            
            # CSV 저장
            df_save.to_csv(f"data/raw/{symbol}_3min.csv", index=False)
            print("완료")
        else:
            print("실패 (데이터 없음)")
        
        # API 호출 제한 방지
        time.sleep(0.3)

    print("\n🎉 모든 데이터 수집이 완료되었습니다!")
    print("이제 'python train.py'를 실행하여 똑똑해진 AI를 학습시키세요.")

if __name__ == "__main__":
    run()