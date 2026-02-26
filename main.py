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
from config import DEVICE, SEQ_LEN, TOP_N
from sheet_logger import log_to_sheet
# [핵심] 전처리기는 collector에서 가져옵니다
from collector import preprocess_data 

def load_model():
    print("🧠 AI 모델을 메모리에 로드합니다...")
    try:
        # [수정] 모델 스펙 변경 (입력 10개, 은닉 64개, Dropout 적용)
        # train.py에서 학습시킨 설정과 똑같아야 에러가 안 납니다.
        model = ScalpingLSTM(input_size=10, hidden_size=64, num_layers=2, output_size=1, dropout=0.2).to(DEVICE)
        
        model.load_state_dict(torch.load("scalping_model.pth", map_location=DEVICE))
        model.eval()
        print("✅ 모델 로딩 완료! (10 Features Ver.)")
        return model
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        print("💡 힌트: train.py를 먼저 실행해서 scalping_model.pth를 만드셨나요?")
        return None

def predict(model, input_tensor):
    """
    [AI 예측 함수]
    collector가 만들어준 텐서(input_tensor)를 넣고 점수를 받습니다.
    """
    try:
        with torch.no_grad():
            model.eval()
            output = model(input_tensor)
            prediction = output.item() # AI 예측가 (0~1)
            
            # 현재 가격 (마지막 시점의 0번째 피쳐 = 정규화된 종가)
            # input_tensor shape: (Batch, Seq, Feature) -> (0, -1, 0)
            current_scaled_price = input_tensor[0, -1, 0].item()
            
            # 점수 = 상승 여력 (예측가 - 현재가)
            score = prediction - current_scaled_price
            
            return score

    except Exception as e:
        # print(f"⚠️ 예측 에러: {e}")
        return 0.0

def get_total_balance(api):
    try:
        balance = api.get_all_balance()
        # 모의투자는 output2, 실전은 output2 등 구조 확인 필요
        # 안전하게 예외처리
        if 'output2' in balance and len(balance['output2']) > 0:
            return int(balance['output2'][0]['tot_evlu_amt'])
        return 0
    except:
        return 0

def main():
    api = KISApi()

    # [1] 자산 조회 및 투자금 설정
    start_balance = get_total_balance(api)
    if start_balance > 0:
        INVEST_AMOUNT_PER_STOCK = start_balance / 19
    else:
        INVEST_AMOUNT_PER_STOCK = 500000 

    print(f"💰 현재 총 자산: {start_balance:,}원")
    print(f"💰 종목당 투자금: {int(INVEST_AMOUNT_PER_STOCK):,}원")
    send_message("🚀 봇 시스템 준비 완료", f"**현재 자산:** {start_balance:,}원\n09:00 장 시작 대기 중...", color=0x0000ff)

    model = load_model()
    if model is None:
        return

    mid_report_sent = False

    print("⏳ 장 시작 대기 및 종목 감시 중...")
    
    while True:
        now = datetime.now()

        # ======================================================
        # [0] 시장 지수 업데이트 (1분마다 갱신)
        # ======================================================
        ksp, ksd = api.get_market_index()
        print(f"\r📊 시장 지수 업데이트: {ksp} ({ksd}%)", end='')
        current_market_rates = (ksp, ksd)
            # 0.0이 아닐 때만 업데이트 (가끔 API 실패 시 기존 값 유지)
        if not current_market_rates:
            current_market_rates = (0.00, 0.00)

        # ======================================================
        # [1] 장 시작 전 / 장 마감 후 처리
        # ======================================================
        if now.hour < 9:
            remain_seconds = (datetime(now.year, now.month, now.day, 9, 0, 0) - now).total_seconds()
            print(f"\r⏰ 장 시작 전입니다! {int(remain_seconds)}초 남았습니다... ", end='')
            time.sleep(1)
            continue

        if now.hour >= 15 and now.minute >= 30:
             print("\n🌙 정규장이 종료되었습니다. 프로그램을 종료합니다.")
             break

        # ======================================================
        # [2] 정기 보고 및 청산
        # ======================================================    
        # 점심 보고
        if now.hour == 12 and now.minute == 0:
            if not mid_report_sent:
                curr_bal = get_total_balance(api)
                profit = curr_bal - start_balance
                prof_rate = (profit/start_balance*100) if start_balance>0 else 0
                msg = f"**🍱 점심 보고**\n손익: {profit:+,}원 ({prof_rate:+.2f}%)"
                send_message("점심 보고", msg, 0x00ff00)
                log_to_sheet("중간점검", start_balance, curr_bal, profit)
                mid_report_sent = True 
        if now.hour == 12 and now.minute > 1: mid_report_sent = False

        # 마감 청산 (15:20)
        if now.hour == 15 and now.minute >= 20:
            print("\n⏰ 장 마감! 전량 매도합니다.")
            api.cancel_all_unfilled_orders()
            time.sleep(2)
            api.sell_all_holdings()
            time.sleep(5)
            
            end_bal = get_total_balance(api)
            profit = end_bal - start_balance
            prof_rate = (profit/start_balance*100) if start_balance>0 else 0
            
            msg = f"**🏁 마감 정산**\n최종 손익: {profit:+,}원 ({prof_rate:+.2f}%)"
            send_message("마감 정산", msg, 0x00ff00 if profit>=0 else 0xff0000)
            log_to_sheet("마감정산", start_balance, end_bal, profit)
            break
        
        # 미체결 청소 (10분 주기)
        if (now.minute % 10 == 0) and (now.second < 10):
             api.cancel_all_unfilled_orders()

        # ==========================================
        # [3단계] 보유 종목 관리 (매도 판정)
        # ==========================================
        my_stocks = api.get_my_stocks()
        if my_stocks:
            print(f"\n💼 보유 종목 관리 중 ({len(my_stocks)}개)...")
            for symbol, info in my_stocks.items():
                stock_name = info.get('name', symbol)
                # trader.py의 manage_risk 호출 (시장 지수 전달)
                manage_risk(api, symbol, info['qty'], info['buy_price'], model, predict, stock_name, current_market_rates)
                time.sleep(0.2)

        # ==========================================
        # [4단계] 신규 종목 발굴 (매수 판정)
        # ==========================================
        # ==========================================
        # [5단계] 신규 종목 발굴 (매수 판정)
        # ==========================================
        mode, threshold = check_mode(api)
        
        if mode == "DEFENSE" and len(my_stocks) >= 3:
            print("🛡️ [방어 모드] 보유 종목이 많아 신규 매수를 자제합니다.")
        else:
            print(f"\n🔍 종목 스캔 중... (모드: {mode}, 시장: 코스피 {current_market_rates[0]}%)")
            
            target_stocks = api.get_top_100()[:TOP_N]
            MAX_HOLDINGS = 19 
            
            # ---------------------------------------------------------
            # [최적화] 잔고 조회는 루프 밖에서 딱 1번만 수행! (API 과부하 방지)
            # ---------------------------------------------------------
            current_deposit = 0
            try:
                balance_info = api.get_balance()
                if balance_info:
                    # 모의/실전 데이터 구조 차이 통합 처리
                    if 'output' in balance_info:
                        val = balance_info['output'].get('ord_psbl_cash') or balance_info['output'].get('dnca_tot_amt')
                    else:
                        val = balance_info['output2'][0].get('ord_psbl_cash') or balance_info['output2'][0].get('dnca_tot_amt')
                    current_deposit = int(val or 0)
            except:
                current_deposit = 0
            # ---------------------------------------------------------

            for symbol in target_stocks:
                if symbol in my_stocks: continue
                
                # 미체결 포함 풀방 체크
                unfulled = api.current_unfilled_orders()
                if len(my_stocks) + int(unfulled) >= MAX_HOLDINGS:
                    print(f"   🔒 [매수 제한] 포트폴리오 가득 참.")
                    break 

                # API 호출 속도 조절 (너무 빠르면 차단됨)
                time.sleep(0.1) 

                # 1. 데이터 전처리 (collector 사용)
                input_tensor = preprocess_data(api, symbol)
                if input_tensor is None: continue
                
                # 2. AI 예측
                score = predict(model, input_tensor)
                
                if score > threshold: 
                    curr_price = api.get_current_price(symbol)
                    if curr_price <= 0: continue

                    # 3. [최적화] API 호출 없이, 아까 저장해둔 변수(current_deposit) 확인
                    target_amt = min(INVEST_AMOUNT_PER_STOCK, current_deposit)
                    
                    if target_amt < 10000:
                        # 돈 없으면 루프 종료 (더 봐봤자 못 삼)
                        print(f"   ⚠️ [매수 중단] 잔고 부족 ({current_deposit:,}원)")
                        break 

                    buy_qty = int(target_amt / curr_price)
                    
                    if buy_qty > 0:
                        print(f"   🚀 [{symbol}] 매수 포착! 점수: {score:.4f}")
                        
                        # 실제 매수 주문
                        result = api.buy_market_order(symbol, qty=buy_qty)
                        
                        if result['status'] == 'success':
                            stock_name = api.get_stock_name(symbol)
                            msg = (
                                f"**🚀 매수 체결**\n"
                                f"종목: {stock_name}\n"
                                f"가격: {curr_price:,}원\n"
                                f"수량: {buy_qty:,}주\n"
                                f"AI점수: {score:.4f}\n"
                                f"모드: {mode}"
                            )
                            send_message("매수 알림", msg, 0x0000ff)
                            
                            # 중복 매수 방지 등록
                            my_stocks[symbol] = {'qty': buy_qty, 'buy_price': curr_price, 'name': stock_name}
                            
                            # [중요] 사용한 금액만큼 내 변수에서 차감 (서버 조회 X)
                            used_amount = curr_price * buy_qty
                            current_deposit -= used_amount
                            print(f"   💰 잔고 차감: -{used_amount:,}원 (남은 돈: {current_deposit:,}원)")
                            
                            time.sleep(1) # 매수 후엔 좀 쉬어줌

        print("💤 10초 대기...")
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("프로그램 종료")
    except Exception as e:
        err = traceback.format_exc()
        print(err)
        send_message("🔥 오류 종료", f"```{err[:1000]}```", 0xff0000)