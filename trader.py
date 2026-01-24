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
def manage_risk(api, symbol, qty, buy_price, model, predict_func, stock_name):
    """
    손절/익절 수행
    """
    current_price = api.get_current_price(symbol)
    if current_price == 0:
        return False

    raw_rate = (current_price - buy_price) / buy_price
    profit_rate = raw_rate * 100
    profit_amount = (current_price - buy_price) * qty
    
    # 이름이 없으면 코드로 대체
    display_name = stock_name if stock_name else symbol

    # ----------------------------------------------------
    # [AI 판단] 현재 이 종목, 더 들고 갈까?
    # ----------------------------------------------------
    df = api.fetch_ohlcv(symbol, timeframe='3m', count=40)
    
    ai_score = 0.0
    if df is not None and len(df) >= 20:
        ai_score = predict_func(model, df)
    
    target_profit_pct = TAKE_PROFIT_RATE * 100
    stop_loss_pct = STOP_LOSS_RATE * 100

    if ai_score > 0.01:
        target_profit_pct = TAKE_PROFIT_RATE * 150 
        stop_loss_pct = STOP_LOSS_RATE * 100   
        status_msg = "🔥 AI: 강력 홀딩 (목표가 상향)"
    elif ai_score > 0.005:
        target_profit_pct = TAKE_PROFIT_RATE * 100
        status_msg = "📈 AI: 상승세 (기본 홀딩)"
    elif ai_score < 0:
        target_profit_pct = TAKE_PROFIT_RATE * 25  
        stop_loss_pct = STOP_LOSS_RATE * 60     
        status_msg = "📉 AI: 하락 반전 (보수적 대응)"
    else:
        status_msg = "😐 AI: 중립"

    # 1. 익절
    if profit_rate >= target_profit_pct:
        api.sell_market_order(symbol, qty) 

        msg = (
            f"**📈 종목:** {display_name} ({symbol})\n"  # [수정] 이름 표시
            f"**💰 수익률:** +{profit_rate:.2f}%\n"
            f"**💵 실현손익:** {profit_amount:+,}원\n"
            f"**📦 매도수량:** {qty}주\n"
            f"**🤖 AI 판단:** {status_msg}\n"
            f"**🤖 AI 점수:** {ai_score:.4f}"
        )
        print(f"🎉 [익절] {display_name} (+{profit_rate:.2f}%) -> {qty}주 전량 매도")
        send_message("🎉 익절 성공! (수익 실현)", msg, color=0x00ff00)
        
        return True

    # 2. 손절
    elif profit_rate <= stop_loss_pct:
        api.sell_market_order(symbol, qty)

        msg = (
            f"**📉 종목:** {display_name} ({symbol})\n" # [수정] 이름 표시
            f"**💧 수익률:** {profit_rate:.2f}%\n"
            f"**💸 손실금액:** {profit_amount:+,}원\n"
            f"**📦 매도수량:** {qty}주\n"
            f"**🤖 AI 판단:** {status_msg}\n"
            f"**🤖 AI 점수:** {ai_score:.4f}"
        )
        print(f"💧 [손절] {display_name} ({profit_rate:.2f}%) -> {qty}주 전량 매도")
        send_message("💧 손절 매도 (리스크 관리)", msg, color=0xff0000)
        
        return True

    return False