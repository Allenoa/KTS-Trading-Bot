# test_real.py
from kis_api import KISApi
import requests
import json
from config import URL_BASE, ACC_NO, APP_KEY, APP_SECRET

def check_account_name():
    print("🕵️ 실전투자 계좌 연동 테스트 중...")
    
    # 1. 토큰 발급
    api = KISApi()
    if not api.access_token:
        print("❌ 토큰 발급 실패! APP KEY/SECRET을 확인하세요.")
        return

    # 2. 계좌 잔고 조회 (실명 확인용)
    # 실전 URL이 맞는지 재확인
    if "openapivts" in URL_BASE:
        print("⚠️ 주의: 현재 '모의투자(VTS)' URL로 설정되어 있습니다!")
    else:
        print("✅ URL 설정: 실전투자(Real) 모드")

    # 잔고 조회 TR
    headers = api.get_headers("TTTC8434R") # 실전용 TR ID
    params = {
        "CANO": ACC_NO,
        "ACNT_PRDT_CD": "01",
        "AFHR_FLPR_YN": "N", "OFL_YN": "N", "INQR_DVSN": "02", "UNPR_DVSN": "01",
        "UNPR_DVSN_VIEW_YN": "Y", "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
    }
    
    try:
        res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-psbl-order", headers=headers, params=params)
        data = res.json()
        
        if data['rt_cd'] == '0':
            # 성공 시
            print("\n🎉 [연동 성공!]")
            print(f"URL: {URL_BASE}")
            print(f"응답 메시지: {data['msg1']}")
            print("이제 run_collector.py를 돌려도 좋습니다.")
        else:
            # 실패 시
            print("\n❌ [연동 실패]")
            print(f"에러 코드: {data['msg_cd']}")
            print(f"에러 메시지: {data['msg1']}")
            print("👉 힌트: '모의투자 미신청'이 뜨면 -> 키가 모의투자용인 겁니다.")
            print("👉 힌트: '유효하지 않은 계좌'가 뜨면 -> 계좌번호 틀림")
            
    except Exception as e:
        print(f"❌ 연결 오류: {e}")

if __name__ == "__main__":
    check_account_name()