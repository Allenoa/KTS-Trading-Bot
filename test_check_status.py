# check_status.py (수정판)
import requests
import json
from config import APP_KEY, APP_SECRET, ACC_NO, URL_BASE

def get_access_token():
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body))
    return res.json()['access_token']

def check_status():
    print("🔍 [종합 진단] 미체결 내역 정밀 조회 중...")
    try:
        token = get_access_token()
    except Exception as e:
        print(f"❌ 토큰 발급 실패: {e}")
        return

    headers = {
        "Content-Type": "application/json", 
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY, 
        "appsecret": APP_SECRET
    }

    # ====================================================
    # 1. 미체결 내역 조회
    # ====================================================
    print("\n⏳ 1. 미체결 내역 (주문 들어갔으나 안 사직 것):")
    
    # 모의투자(VTTC8001R) / 실전투자(TTTC8001R)
    tr_id = "VTTC8001R" if "vts" in URL_BASE else "TTTC8001R"
    headers["tr_id"] = tr_id
    
    url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
    params = {
        "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "INQR_STRT_DT": "20240101", "INQR_END_DT": "20301231",
        "SLL_BUY_DVSN_CD": "00", "INQR_DVSN": "00", "PDNO": "", 
        "CCLD_DVSN": "02", # 02: 미체결만 조회
        "ORD_GNO_BRNO": "", "ODNO": "", "INQR_DVSN_3": "00", "INQR_DVSN_1": "", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
    }
    
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        
        if data['rt_cd'] == '0':
            if 'output1' in data and len(data['output1']) > 0:
                print(f"   🚨 총 {len(data['output1'])}건의 미체결 주문 발견!")
                
                for i, item in enumerate(data['output1']):
                    name = item.get('prdt_name', '종목명없음')
                    code = item.get('pdno', item.get('pdno', '코드없음'))
                    side = "매수" if item.get('sll_buy_dvsn_cd') == '02' else "매도"
                    
                    # [핵심] 잔여 수량 키 찾기 (여러가지 시도)
                    left_qty = item.get('rmnd_loqty') or item.get('ord_remn_qty') or item.get('jan_qty')
                    
                    # 만약 그래도 못 찾으면 주문수량 - 체결수량으로 계산
                    if left_qty is None:
                        ord_qty = int(item.get('ord_qty') or 0)
                        ccld_qty = int(item.get('tot_ccld_qty') or 0)
                        left_qty = ord_qty - ccld_qty

                    print(f"   👉 [{i+1}] {side} 대기 | {name}({code}) | {left_qty}주 미체결")
            else:
                print("   ✅ 미체결 내역 없음 (깨끗함)")
        else:
            print(f"   ⚠️ API 응답 에러: {data.get('msg1')}")
            
    except Exception as e:
        print(f"   ❌ 조회 중 치명적 오류: {e}")

if __name__ == "__main__":
    check_status()