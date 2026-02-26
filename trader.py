# trader.py
import time
from notifier import send_message
from config import TAKE_PROFIT_RATE, STOP_LOSS_RATE
# [핵심] collector를 가져와야 AI에게 올바른 데이터를 줄 수 있습니다.
from collector import preprocess_data

def check_available_budget(api, target_amount):
    balance = api.get_balance()
    try:
        # 모의/실전 데이터 구조 차이 통합 처리
        if 'output' in balance:
            val = balance['output'].get('ord_psbl_cash') or balance['output'].get('dnca_tot_amt')
        else:
            val = balance['output2'][0].get('ord_psbl_cash') or balance['output2'][0].get('dnca_tot_amt')
        
        available_cash = int(val or 0)
        return (available_cash >= target_amount), available_cash
    except Exception as e:
        return False, 0

def check_mode(api):
    balance = api.get_balance()
    deposit = 0
    try:
        if 'output' in balance:
            val = balance['output'].get('ord_psbl_cash') or balance['output'].get('dnca_tot_amt')
        elif 'output2' in balance:
             val = balance['output2'][0].get('ord_psbl_cash') or balance['output2'][0].get('dnca_tot_amt')
        deposit = int(val or 0)
    except:
        deposit = 0

    stock_value = 0
    my_stocks = api.get_my_stocks()
    if my_stocks:
        for symbol, info in my_stocks.items():
            curr_price = api.get_current_price(symbol)
            if curr_price == 0: curr_price = info['buy_price']
            stock_value += curr_price * info['qty']

    total_asset = deposit + stock_value
    if total_asset == 0: return "ATTACK", 0.005

    cash_ratio = deposit / total_asset
    if cash_ratio < 0.3: return "DEFENSE", 0.008  
    else: return "ATTACK", 0.005   

def manage_risk(api, symbol, qty, buy_price, model, predict_func, stock_name, market_rates):
    """
    [리스크 관리 v5]
    - AI 점수 계산 시 collector.preprocess_data 사용 (0.0 버그 수정)
    - 시장 지수 반영 로직 유지
    """
    current_price = api.get_current_price(symbol)
    if current_price == 0: return False

    # 수익률 계산
    raw_rate = (current_price - buy_price) / buy_price
    profit_rate = raw_rate * 100
    profit_amount = (current_price - buy_price) * qty
    display_name = stock_name if stock_name else symbol

    # ---------------------------------------------------------
    # [1] AI 예측 점수 확인 (수정된 부분)
    # ---------------------------------------------------------
    ai_score = 0.0
    
    # 예전 방식(Raw DF)이 아니라, collector를 통해 Tensor를 받아야 함
    input_tensor = preprocess_data(api, symbol)
    
    if input_tensor is not None:
        # main.py에서 넘겨준 predict 함수 사용
        ai_score = predict_func(model, input_tensor)
    
    # 로그 확인용 (이제 0.0000이 아니라 숫자가 나와야 함)
    # print(f"   🤖 {display_name} AI점수: {ai_score:.4f}")

    # ---------------------------------------------------------
    # [2] 시장 지수(Environment) 반영
    # ---------------------------------------------------------
    kospi, kosdaq = market_rates
    avg_market = (kospi + kosdaq) / 2
    
    base_target = TAKE_PROFIT_RATE * 100 
    base_stop = STOP_LOSS_RATE * 100
    
    market_msg = ""

    # 시장 상황에 따른 베이스라인 조정
    if avg_market >= 0.5:
        base_stop *= 1.1 
        market_msg = "📈"
    elif avg_market <= -0.5:
        base_target *= 0.9 
        base_stop *= 0.8
        market_msg = "📉"
    
    # ---------------------------------------------------------
    # [3] AI 점수(Actor) 반영 -> 최종 목표가/손절가 결정
    # ---------------------------------------------------------
    final_target = base_target
    final_stop = base_stop
    status_msg = "😐 AI:중립"

    if ai_score >= 0.01:
        final_target = base_target * 1.5
        if final_stop > -3.0: final_stop = -3.0 
        status_msg = "🔥 AI:상승"
    elif ai_score >= 0.005:
        final_target = base_target * 1.2
        status_msg = "📈 AI:양호"
    elif ai_score < -0.005: # AI가 하락 예측하면 목표가 낮춤
        final_target = base_target * 0.8
        final_stop = base_stop * 0.9
        status_msg = "📉 AI:하락"

    # ---------------------------------------------------------
    # [4] 트레일링 스탑 (수익 보존)
    # ---------------------------------------------------------
    if profit_rate >= 2.0:
        if final_stop < 0.5: 
            final_stop = 0.5 
            status_msg += "(🔒수익보존)"
    if profit_rate >= 5.0:
        final_stop = 3.0

    # ---------------------------------------------------------
    # [5] 매매 실행
    # ---------------------------------------------------------
    if profit_rate >= final_target:
        # 익절
        api.sell_market_order(symbol, qty) 
        msg = (
            f"**🎉 익절 성공!** {market_msg}\n"
            f"종목: {display_name}\n"
            f"수익: +{profit_rate:.2f}% ({profit_amount:+,}원)\n"
            f"AI: {status_msg} ({ai_score:.4f})\n"
            f"(목표: {final_target:.2f}%)"
        )
        send_message("💰 익절 알림", msg, color=0x00ff00)
        return True

    elif profit_rate <= final_stop:
        # 손절
        api.sell_market_order(symbol, qty)
        
        title = "🛡️ 수익 보존 매도" if profit_rate > 0 else "💧 손절 매도"
        color = 0x00ff00 if profit_rate > 0 else 0xff0000
        
        msg = (
            f"**{title}** {market_msg}\n"
            f"종목: {display_name}\n"
            f"수익: {profit_rate:.2f}% ({profit_amount:+,}원)\n"
            f"AI: {status_msg} ({ai_score:.4f})\n"
            f"(기준: {final_stop:.2f}%)"
        )
        send_message(title, msg, color=color)
        return True

    # 로그 출력 (선택 사항)
    print(f"목표: {final_target:.2f}%, 손절: {final_stop:.2f}%, 수익: {profit_rate:.2f}% ({ai_score:.4f})")
    return False