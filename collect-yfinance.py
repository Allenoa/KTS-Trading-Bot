# collect_yfinance.py
import yfinance as yf
import pandas as pd
import os
import time
from kis_api import KISApi

def run_yfinance_collector():
    print("🚀 [Yahoo Finance] 데이터 수집기 가동")
    
    # 1. KIS API에서 '종목 리스트'만 가져오기 (이건 잘 되니까)
    kis = KISApi()
    codes = kis.get_top_100()
    
    if not codes or len(codes) < 5:
        print("⚠️ 종목 리스트 확보 실패 -> 수동 리스트 사용")
        codes = ["005930", "000660", "005380", "035420", "000270", "051910", "006400", "068270", "005490", "032830"]

    print(f"📡 총 {len(codes)}개 종목의 '분봉 데이터'를 다운로드합니다...")
    
    if not os.path.exists("data/raw"):
        os.makedirs("data/raw")

    success_count = 0
    
    for code in codes:
        try:
            # 한국 종목 코드는 뒤에 .KS를 붙여야 함
            ticker = f"{code}.KS"
            print(f"   ⬇️ [{code}] 다운로드 중...", end="")
            
            # [핵심] 최근 7일치, 5분봉 데이터 가져오기 (3분봉은 지원 안할 수 있어 5분봉 사용 - 학습엔 충분함)
            # yfinance 제약: 1분~5분봉은 최근 7일~60일치만 제공됨
            data = yf.download(ticker, period="5d", interval="5m", progress=False)
            
            if len(data) > 10:
                # KIS 포맷에 맞춰 칼럼 이름 변경
                # Open, High, Low, Close, Volume -> stck_oprc, stck_hgpr, stck_lwpr, stck_prpr, cntg_vol
                df = pd.DataFrame()
                df['stck_oprc'] = data['Open']
                df['stck_hgpr'] = data['High']
                df['stck_lwpr'] = data['Low']
                df['stck_prpr'] = data['Close'] # 현재가 = 종가
                df['cntg_vol'] = data['Volume']
                
                # 저장
                save_path = f"data/raw/{code}_3min.csv" # 이름은 3min으로 유지 (코드 호환성 위해)
                df.to_csv(save_path, index=False)
                print(" ✅ 성공")
                success_count += 1
            else:
                print(" ⚠️ 데이터 부족")
                
        except Exception as e:
            print(f" ❌ 실패: {e}")
            
    print(f"\n🎉 수집 완료! (성공: {success_count}/{len(codes)})")
    print("👉 이제 'train.py'를 실행하세요!")

if __name__ == "__main__":
    run_yfinance_collector()