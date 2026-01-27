# main.py
import time
import datetime
from datetime import datetime
import torch
import traceback
import pandas as pd
import numpy as np
from kis_api import KISApi
from trader import check_mode, manage_risk, check_available_budget
from notifier import send_message
from model import ScalpingLSTM
from config import DEVICE
from sheet_logger import log_to_sheet

# [설정]
TOP_N = 30
SEQ_LEN = 20

def load_model():
    print("🧠 AI 모델을 메모리에 로드합니다...")
    try:
        model = ScalpingLSTM(5, 32, 2, 1).to(DEVICE)
        model.load_state_dict(torch.load("scalping_model.pth", map_location=DEVICE))
        model.eval()
        print("✅ 모델 로딩 완료!")
        return model
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        return None

def predict(model, df):
    if len(df) < SEQ_LEN:
        return 0.0

    try:
        df = df.iloc[::-1].reset_index(drop=True)
        cols = ['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'cntg_vol']
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()

        target_df = df.tail(SEQ_LEN)
        
        price_data = target_df[['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr']].values
        volume_data = target_df[['cntg_vol']].values

        price_max = price_data.max()
        price_min = price_data.min()
        vol_max = volume_data.max()

        if price_max == price_min or vol_max == 0:
            return 0.0

        scaled_price = (price_data - price_min) / (price_max - price_min + 1e-8)
        scaled_vol = volume_data / (vol_max + 1e-8)

        x_input = np.hstack([scaled_price, scaled_vol])
        x_tensor = torch.FloatTensor(x_input).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            output = model(x_tensor)
            prediction = output.item()
            current_scaled_price = scaled_price[-1][0]
            score = prediction - current_scaled_price
            return score 

    except Exception as e:
        print(f"⚠️ 예측 중 에러: {e}")
        return 0.0

def calculate_indicators(df):
    """
    RSI(14)와 이동평균선(MA5, MA20)을 계산하여 반환
    """
    try:
        # 데이터가 너무 적으면 계산 불가
        if len(df) < 20:
            return None, None, None

        # 종가 가져오기 (숫자로 변환)
        close = pd.to_numeric(df['stck_prpr'], errors='coerce')

        # 1. 이동평균선 (MA)
        ma5 = close.rolling(window=5).mean().iloc[-1]   # 단기 추세
        ma20 = close.rolling(window=20).mean().iloc[-1] # 장기 추세

        # 2. RSI (14)
        delta = close.diff(1)
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]

        return rsi, ma5, ma20

    except Exception as e:
        print(f"⚠️ 지표 계산 오류: {e}")
        return None, None, None

def get_total_balance(api):
    try:
        balance = api.get_all_balance()
        return int(balance['output2'][0]['tot_evlu_amt'])
    except:
        return 0

def main():
    api = KISApi()

    start_balance = get_total_balance(api)
    # 19개 종목 분산 투자 금액 계산
    if start_balance > 0:
        INVEST_AMOUNT_PER_STOCK = start_balance / 19
    else:
        INVEST_AMOUNT_PER_STOCK = 500000 # 잔고 조회 실패 시 기본값
    print(f"💰 현재 총 자산: {start_balance:,}원")
    print(f"💰 종목당 투자금: {int(INVEST_AMOUNT_PER_STOCK):,}원")
    send_message("🚀 봇 시스템 준비 완료", f"**현재 자산:** {start_balance:,}원\n09:00 장 시작 대기 중...", color=0x0000ff)

    mid_report_sent = False
    model = load_model()
    if model is None:
        return

    print("⏳ 장 시작 대기 및 종목 감시 중...")
    
    while True:
        now = datetime.now()

        ksp, ksd = api.get_market_index()
        current_market_rates = (ksp, ksd)

        # ======================================================
        # [0] 장 시작 전 대기 (09:00 이전)
        # ======================================================
        if now.hour < 9:
            # 현재 시간을 출력하며 대기 (줄바꿈 없이 덮어쓰기 효과)
            remain_seconds = (datetime(now.year, now.month, now.day, 9, 0, 0) - now).total_seconds()
            print(f"\r⏰ 장 시작 전입니다! {int(remain_seconds)}초 남았습니다... ", end='')
            time.sleep(1) # 1초씩 대기
            continue

        # ======================================================
        # [0.5] 장 마감 후 종료 (15:30 이후)
        # ======================================================
        if now.hour >= 15 and now.minute >= 30:
             print("\n🌙 정규장이 종료되었습니다. 프로그램을 종료합니다.")
             break

        # ======================================================
        # [1] 12시 점심 중간 점검
        # ======================================================    
        if now.hour == 12 and now.minute == 0:
            if not mid_report_sent:
                current_balance = get_total_balance(api)
                profit = current_balance - start_balance
                profit_rate = (profit / start_balance * 100) if start_balance > 0 else 0
                
                msg = (
                    f"**💰 시작 자산:** {start_balance:,}원\n"
                    f"**💵 현재 자산:** {current_balance:,}원\n"
                    f"**📈 현재 손익:** {profit:+,}원 ({profit_rate:+.2f}%)"
                )
                color = 0x00ff00 if profit >= 0 else 0xffff00
                send_message("🍱 점심 중간 점검", msg, color)
                log_to_sheet("중간점검", start_balance, current_balance, profit)
                mid_report_sent = True 
        
        if now.hour == 12 and now.minute > 1:
            mid_report_sent = False

        # ======================================================
        # [2] 장 마감 청산 (15:20) - 강제 매도 및 리포트
        # ======================================================
        if now.hour == 15 and now.minute >= 20:
            print("⏰ 장 마감! 전량 매도합니다.")
            # 미체결 취소 먼저
            api.cancel_all_unfilled_orders()
            time.sleep(2)
            
            # 보유주식 전량 매도
            api.sell_all_holdings()
            time.sleep(5)
            
            end_balance = get_total_balance(api)
            profit = end_balance - start_balance
            profit_rate = (profit / start_balance * 100) if start_balance > 0 else 0
            
            msg = (
                f"**💰 시작 자산:** {start_balance:,}원\n"
                f"**💵 종료 자산:** {end_balance:,}원\n"
                f"**📈 최종 손익:** {profit:+,}원 ({profit_rate:+.2f}%)"
            )
            color = 0x00ff00 if profit >= 0 else 0xff0000
            send_message("🏁 장 마감 정산", msg, color)
            log_to_sheet("마감정산", start_balance, end_balance, profit)
            break
        
        # ======================================================
        # [3] 미체결 청소 (10분 주기)
        # ======================================================
        if (now.minute % 10 == 0) and (now.second < 30):
             print(f"🧹 [정기 청소] {now.strftime('%H:%M')} - 오래된 미체결 주문 정리")
             api.cancel_all_unfilled_orders()
             time.sleep(5)
    
        # ==========================================
        # [4단계] 보유 종목 관리 (매도 판정)
        # ==========================================
        my_stocks = api.get_my_stocks()
        if my_stocks:
            print(f"\n💼 보유 종목 관리 중 ({len(my_stocks)}개)...")
            for symbol, info in my_stocks.items():
                # [수정] info에 있는 'name'을 꺼내서 전달합니다. (없으면 symbol 사용)
                stock_name = info.get('name', symbol)
                manage_risk(api, symbol, info['qty'], info['buy_price'], model, predict, stock_name, current_market_rates)
                time.sleep(0.3)

        # ==========================================
        # [5단계] 신규 종목 발굴 (매수 판정)
        # ==========================================
        mode, threshold = check_mode(api)
        
        if mode == "DEFENSE" and len(my_stocks) >= 3:
            print("🛡️ [방어 모드] 보유 종목이 많아 신규 매수를 자제합니다.")
        else:
            print(f"\n🔍 종목 스캔 중... (모드: {mode})")
            target_stocks = api.get_top_100()[:TOP_N]
            
            MAX_HOLDINGS = 19 

            for symbol in target_stocks:
                if symbol in my_stocks: continue
                
                # 미체결+보유수량 체크
                unfulled_orders = api.current_unfilled_orders()
                if len(my_stocks) + int(unfulled_orders) >= MAX_HOLDINGS:
                    print(f"   🔒 [매수 제한] 풀방입니다.")
                    break 

                # 1. 차트 데이터 가져오기
                df = api.fetch_ohlcv(symbol)
                if df is None or len(df) < SEQ_LEN: continue
                
                # ---------------------------------------------------------
                # [★ 필터링 1] 보조지표로 1차 거르기 (똥차 피하기)
                # ---------------------------------------------------------
                rsi, ma5, ma20 = calculate_indicators(df)
                curr_price = api.get_current_price(symbol)
                
                if rsi is not None:
                    # 조건 A: "떨어지는 칼날" 금지 (현재가가 20일 이동평균선보다 아래면 패스)
                    if curr_price < ma20:
                        # print(f"   🚫 [필터] 하락 추세 ({symbol}): 가격 < 20이동평균")
                        continue
                    
                    # 조건 B: "꼭지" 금지 (RSI가 70 이상이면 과매수 구간이라 곧 떨어짐)
                    if rsi >= 70:
                        # print(f"   🚫 [필터] 과열 구간 ({symbol}): RSI {rsi:.1f} >= 70")
                        continue
                        
                    # 조건 C: "바닥 뚫기" 금지 (RSI가 30 이하면 너무 약함 -> 반등 확인 필요)
                    if rsi <= 30:
                        continue
                # ---------------------------------------------------------

                # 2. AI 예측 (살아남은 종목만 AI 검사)
                score = predict(model, df)
                
                if score > threshold: 
                    if curr_price > 0:
                        balance_info = api.get_balance()
                        deposit = 0
                        if balance_info:
                            if 'output' in balance_info:
                                val = balance_info['output'].get('ord_psbl_cash') or balance_info['output'].get('dnca_tot_amt')
                                deposit = int(val or 0)
                            if deposit == 0 and 'output2' in balance_info and len(balance_info['output2']) > 0:
                                val = balance_info['output2'][0].get('ord_psbl_cash') or balance_info['output2'][0].get('dnca_tot_amt')
                                deposit = int(val or 0)
                        
                        target_amount = min(INVEST_AMOUNT_PER_STOCK, deposit)
                        
                        if target_amount < 10000:
                            print(f"   ⚠️ [매수 포기] 잔고 부족")
                            continue 

                        buy_qty = int(target_amount / curr_price)
                        
                        if buy_qty > 0:
                            print(f"   🚀 [{symbol}] 매수 시도: {curr_price:,}원 x {buy_qty}주 (점수: {score:.4f} | RSI: {rsi:.1f})")
                            
                            result = api.buy_market_order(symbol, qty=buy_qty)
                            
                            if result['status'] == 'success':
                                print(f"   ✅ 매수 주문 접수 완료!")
                                stock_name = api.get_stock_name(symbol)
                                
                                msg = (
                                    f"**📈 종목:** {stock_name} ({symbol})\n"
                                    f"**💵 매수가:** {curr_price:,}원\n"
                                    f"**📦 수량:** {buy_qty}주\n"
                                    f"**🤖 AI 점수:** {score:.4f}\n"
                                    f"**📊 지표:** RSI {rsi:.1f}\n" # RSI 정보 추가
                                    f"**🛡️ 모드:** {mode}"
                                )
                                send_message(f"🚀 매수 주문 접수", msg, color=0x0000ff)
                                
                                my_stocks[symbol] = {'qty': buy_qty, 'buy_price': curr_price, 'name': stock_name}
                                time.sleep(1)
                            else:
                                print(f"   ⚠️ 주문 거절됨")

        print("💤 10초 대기...")
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("종료됨")
    except Exception as e:
        error_log = traceback.format_exc()
        print(error_log)
        send_message("🔥 시스템 비정상 종료", f"```{error_log[:1500]}```", color=0xff0000)