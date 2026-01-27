# trader.py
from notifier import send_message
from config import TAKE_PROFIT_RATE, STOP_LOSS_RATE

def check_available_budget(api, target_amount):
    """자금 검증"""
    balance = api.get_balance()
    try:
        available_cash = int(balance['output']['ord_psbl_cash'])
        return (available_cash >= target_amount), available_cash
    except Exception as e:
        print(f"⚠️ 잔고 조회 중 오류: {e}")
        return False, 0

def check_mode(api):
    """자금 관리 모드"""
    balance = api.get_balance()
    try:
        deposit = int(balance['output']['ord_psbl_cash'])
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

    if total_asset == 0:
        return "ATTACK", 0.005

    cash_ratio = deposit / total_asset

    if cash_ratio < 0.3:
        return "DEFENSE", 0.008  
    else:
        return "ATTACK", 0.005   

# [수정] stock_name 인자 추가
def manage_risk(api, symbol, qty, buy_price, model, predict_func, stock_name, market_rates):
    """
    [리스크 관리 v4] AI 중심 + 시장 상황 반영
    1. 시장 상황에 따라 '기본 베이스(익절/손절 폭)'를 살짝 조정
    2. 그 위에 AI 점수를 곱해서 최종 목표 확정
    """
    current_price = api.get_current_price(symbol)
    if current_price == 0: return False

    # 현재 종목 수익률
    raw_rate = (current_price - buy_price) / buy_price
    profit_rate = raw_rate * 100
    profit_amount = (current_price - buy_price) * qty
    display_name = stock_name if stock_name else symbol

    # 1. AI 예측 점수 확인
    df = api.fetch_ohlcv(symbol, timeframe='3m', count=40)
    ai_score = 0.0
    if df is not None and len(df) >= 20:
        ai_score = predict_func(model, df)
    
    # ---------------------------------------------------------
    # [1단계] 시장 지수(Environment) 반영 -> '기본 베이스'만 조정
    # ---------------------------------------------------------
    kospi, kosdaq = market_rates
    avg_market = (kospi + kosdaq) / 2
    
    # 설정값 가져오기 (예: 익절 4.0%, 손절 -2.0%)
    base_target = TAKE_PROFIT_RATE * 100 
    base_stop = STOP_LOSS_RATE * 100
    
    market_msg = ""

    # 시장이 좋을 때: 손절 라인을 조금 여유롭게 줌 (흔들려도 버티게)
    if avg_market >= 0.3:
        # 익절폭은 그대로(AI가 정함), 손절폭만 10% 늘림 (예: -2.0% -> -2.2%)
        base_stop *= 1.1 
        market_msg = "📈 시장 상승세"

    # 시장이 나쁠 때: 목표를 조금 낮추고, 손절을 타이트하게 잡음
    elif avg_market <= 0:
        base_target *= 0.9 # 목표 10% 하향 (예: 4.0% -> 3.6%)
        base_stop *= 0.8   # 손절 20% 축소 (예: -2.0% -> -1.6% 칼손절)
        market_msg = "📉 시장 하락세"
    
    # ---------------------------------------------------------
    # [2단계] AI 점수(Actor) 반영 -> 최종 매도 결정 (여기가 메인)
    # ---------------------------------------------------------
    
    final_target = base_target
    final_stop = base_stop
    status_msg = "😐 AI: 중립"

    # AI가 강력 추천하면 시장이 안 좋아도 목표가 대폭 상향
    if ai_score >= 0.01:
        final_target = base_target * 1.5  # (예: 3.6% -> 5.4%)
        # AI 믿고 손절폭도 넓혀줌 (버티기)
        if final_stop > -3.0: 
            final_stop = -3.0 
        status_msg = "🔥 AI: 강력 상승"

    elif ai_score >= 0.005:
        final_target = base_target * 1.2
        status_msg = "📈 AI: 상승세"

    elif ai_score < 0:
        # AI도 안 좋게 보면 목표/손절 모두 줄임
        final_target = base_target * 0.8
        final_stop = base_stop * 0.9
        status_msg = "📉 AI: 하락세"

    # ---------------------------------------------------------
    # [3단계] 트레일링 스탑 (수익 보존)
    # ---------------------------------------------------------
    # 이미 2% 이상 수익 중이라면, 절대 손해 보고 팔지 않게 세팅
    if profit_rate >= 2.0:
        if final_stop < 0.5: 
            final_stop = 0.5 
            status_msg += " (🔒 수익보존)"

    # 이미 5% 이상 수익 중이라면 익절 라인 대폭 상향
    if profit_rate >= 5.0:
        final_stop = 3.0

    # ---------------------------------------------------------
    # [4단계] 매매 실행
    # ---------------------------------------------------------
    
    # 1. 익절 달성
    if profit_rate >= final_target:
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

    # 2. 손절 달성
    elif profit_rate <= final_stop:
        api.sell_market_order(symbol, qty)
        
        title = "🛡️ 수익 보존 매도" if profit_rate > 0 else "💧 손절 매도 "
        color = 0x00ff00 if profit_rate > 0 else 0xff0000
        
        msg = (
            f"**{title}** ({market_msg})\n"
            f"종목: {display_name}\n"
            f"수익: {profit_rate:.2f}% ({profit_amount:+,}원)\n"
            f"AI: {status_msg}\n"
            f"(기준: {final_stop:.2f}%)"
        )
        send_message(title, msg, color=color)
        return True

    return False