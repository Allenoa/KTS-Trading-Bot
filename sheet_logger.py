# sheet_logger.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yfinance as yf
from datetime import datetime

# 1. 인증 설정 (JSON 파일 필요)
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
        client = gspread.authorize(creds)
        # [중요] 스프레드 시트 이름을 정확히 적으세요 (예: "주식매매일지")
        sheet = client.open("주식매매일지").sheet1 
        return sheet
    except Exception as e:
        print(f"⚠️ 구글 시트 연결 실패: {e} (JSON 키 파일과 공유 설정을 확인하세요)")
        return None

# 2. 시장 지수 가져오기 (야후 파이낸스)
# 2. 시장 지수 및 등락률 가져오기 (야후 파이낸스)
def get_market_indices():
    """
    코스피, 코스닥의 현재 지수와 전일 대비 등락률(%)을 계산하여 반환합니다.
    """
    try:
        # 최근 5일치 데이터를 가져와서 안전하게 어제 종가를 확보합니다.
        ks_df = yf.Ticker("^KS11").history(period="5d")
        kq_df = yf.Ticker("^KQ11").history(period="5d")
        
        def calculate_change(df):
            if len(df) < 2:
                return "0.00", "0.00%"
            
            # iloc[-1]: 오늘 현재가, iloc[-2]: 어제 종가
            curr_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            
            # 등락률 계산: (현재가 - 어제종가) / 어제종가 * 100
            change_rate = ((curr_price - prev_close) / prev_close) * 100
            
            # 포맷팅 (예: 2500.50, +1.25%)
            return f"{curr_price:.2f}", f"{change_rate:+.2f}%"

        ks_val, ks_rate = calculate_change(ks_df)
        kq_val, kq_rate = calculate_change(kq_df)
        
        return ks_val, ks_rate, kq_val, kq_rate
        
    except Exception as e:
        print(f"⚠️ 지수 조회 실패: {e}")
        return "0.00", "0.00%", "0.00", "0.00%"

# 3. 로그 기록 함수
# 3. 로그 기록 함수
def log_to_sheet(report_type, start_money, current_money, profit):
    sheet = get_sheet()
    if sheet is None: return

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    # 내 수익률
    profit_rate = (profit / start_money * 100) if start_money > 0 else 0
    
    # 시장 지수 (지수, 등락률)
    ks_val, ks_rate, kq_val, kq_rate = get_market_indices()
    
    # 행 데이터 생성 (컬럼이 늘어납니다)
    row = [
        date_str, 
        time_str, 
        report_type,          # 구분 (중간/마감)
        f"{start_money:,}",   # 시작자산
        f"{current_money:,}", # 현재자산
        f"{profit:,}",        # 손익금
        f"{profit_rate:+.2f}%",# 내 수익률
        f"{ks_val} ({ks_rate})", # 코스피 (예: 2500.00 (+1.2%))
        f"{kq_val} ({kq_rate})"  # 코스닥 (예: 800.00 (-0.5%))
    ]
    
    try:
        sheet.append_row(row)
        print(f"📝 구글 시트 기록 완료! (코스피: {ks_rate}, 코스닥: {kq_rate})")
    except Exception as e:
        print(f"❌ 시트 기록 중 에러: {e}")