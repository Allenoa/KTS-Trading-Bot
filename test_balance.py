# check_balance.py (진단용)
import requests
import json
from config import APP_KEY, APP_SECRET, ACC_NO, URL_BASE

def test_balance():
    print("🔎 잔고 조회 정밀 진단 시작...")
    
    # 1. 토큰 발급
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body))
    token = res.json()['access_token']
    
    # 2. 잔고 조회 시도 (VTTC8404R)
    url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "Content-Type": "application/json", 
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY, 
        "appsecret": APP_SECRET, 
        "tr_id": "VTTC8434R" # 여기가 핵심
    }
    params = {
        "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "AFHR_FLPR_YN": "N", "OFL_YN": "N", 
        "INQR_DVSN": "02", "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N", 
        "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
    }
    
    print(f"📡 요청 보내는 중... (TR_ID: VTTC8434R)")
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    
    print("\n📝 결과 리포트:")
    print(f"응답 코드: {data['rt_cd']}")
    print(f"메시지: {data['msg1']}")
    print(f"총 잔고 조회: {data['output2'][0]['tot_evlu_amt']}원")
    if 'output1' in data:
        print("보유 종목 리스트:")
        for item in data['output1']:
            print(f"- {item['pdno']}: {item['hldg_qty']}주")
    else:
        print("데이터 없음 (또는 에러)")

if __name__ == "__main__":
    test_balance()