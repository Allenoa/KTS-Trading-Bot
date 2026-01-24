import requests
import json
from config import APP_KEY, APP_SECRET, ACC_NO, URL_BASE

def debug_cash():
    print("🕵️‍♂️ [자산 조회 디버깅] 서버 응답을 낱낱이 파헤칩니다...\n")
    
    # 1. 토큰 발급
    try:
        headers = {"content-type": "application/json"}
        body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
        res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body))
        token = res.json()['access_token']
    except Exception as e:
        print(f"❌ 토큰 발급부터 실패함: {e}")
        return

    # 2. 잔고 조회 시도
    # 모의투자(VTTC8434R)
    if "vts" in URL_BASE:
        print("👉 모의투자(VTS) 환경 감지됨")
        tr_id = "VTTC8908R"
        url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        
        # [테스트 1] 가장 유력한 파라미터 조합
        params = {
        "CANO": ACC_NO,
        "ACNT_PRDT_CD": "01",
        "PDNO": "005930",
        "ORD_UNPR": "65500",
        "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "Y",
        "OVRS_ICLD_YN": "Y"
    }
    else:
        print("👉 실전투자(Real) 환경 감지됨")
        tr_id = "TTTC8434R"
        url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        params = {
            "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "AFHR_FLPR_YN": "N", "OFL_YN": "N", 
            "INQR_DVSN": "02", "UNPR_DVSN": "01", "UNPR_DVSN_VIEW_YN": "Y", 
            "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", 
            "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
        }

    headers = {
        "Content-Type": "application/json", 
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY, 
        "appsecret": APP_SECRET, 
        "tr_id": tr_id
    }
    
    # 3. 요청 전송 및 원본 데이터 출력
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        
        cash1 = data['output']['ord_psbl_cash']
        # cash2 = data['output2']['ord_psbl_cash']

        print("-" * 50)
        print(f"📡 응답 코드 (rt_cd): {data.get('rt_cd')}")
        print(f"💬 에러 메시지 (msg1): {data.get('msg1')}")
        print("-" * 50)
        
        # 여기서 KeyError가 안 나게 안전하게 확인
        if 'output' in data:
            print("✅ 데이터 수신 성공!")
            print(cash1)
            # print(cash2)
        else:
            print("❌ 'output' 데이터가 없습니다! (위 에러 메시지를 확인하세요)")
            print("🔍 서버가 보낸 전체 내용:\n", data)
            
    except Exception as e:
        print(f"❌ 요청 중 파이썬 에러 발생: {e}")

if __name__ == "__main__":
    debug_cash()