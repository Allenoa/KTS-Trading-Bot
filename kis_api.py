# kis_api.py
import requests
import json
import time
import pandas as pd
import numpy as np
import yfinance as yf # 야후 파이낸스 추가
from config import APP_KEY, APP_SECRET, ACC_NO, URL_BASE
from notifier import send_message

class KISApi:
    def __init__(self):
        print(f"\n📡 [시스템 연결] {URL_BASE}")
        if "vts" in URL_BASE:
            print("   👉 모의투자(VTS) 모드로 동작합니다.")
        else:
            print("   👉 실전투자(Real) 모드로 동작합니다.")
            
        self.access_token = self.get_access_token()
    
    def get_access_token(self):
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET
        }
        try:
            res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, data=json.dumps(body))
            data = res.json()
            if 'access_token' in data:
                return data['access_token']
            else:
                print(f"❌ 토큰 발급 실패: {data.get('error_description')}")
                return None
        except Exception as e:
            print(f"❌ 연결 실패: {e}")
            return None

    def get_headers(self, tr_id):
        return {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "tr_id": tr_id
        }
    
    def is_dirty_stock(self, name):
        """
        [필터링 함수] 종목명에 ETF, ETN, 스팩 등이 포함되어 있는지 검사
        True 반환 -> 더러운 종목 (제외 대상)
        False 반환 -> 깨끗한 주식 (수집 대상)
        """
        # 1. 이름이 없으면 위험하니까 제외
        if not name: 
            return True
        
        # 2. 대문자로 변환 (KODEX, kodex 모두 잡기 위함)
        name_upper = name.upper()
        
        # 제외할 키워드 목록
        exclude_keywords = [
            "ETN", "스팩", "인버스", "레버리지", "선물", "우B", "우선주", "리츠", "홀딩스", # 기타 상품
            "TRUE", "QV", "SMART", "삼성머스트", "신한제", "유안타제", "하나금융", "엔에이치" # 스팩 관련
        ]
        
        # 3. 우선주 체크 (종목명 끝에 '우' 혹은 '우B'가 붙음)
        if name.endswith("우") or name.endswith("우B"):
            return True

        # 4. 키워드 포함 여부 체크
        for keyword in exclude_keywords:
            if keyword in name_upper:
                return True # 더러운 종목
        
        return False # 깨끗한 종목

    def get_top_100(self):
        """
        [종목 발굴 엔진 업그레이드] 
        유명 우량주 + 거래량 급증주 + 가격 급등주를 혼합하여 추출
        """
        all_symbols = set() # 중복 제거를 위해 set 사용
        
        # 1. 고정 우량주 (삼성전자, 하이닉스 등 필수 종목)
        blue_chips = [
            "005930", # 삼성전자
            "000660", # SK하이닉스
            "373220", # LG에너지솔루션 (배터리 대장)
            "207940", # 삼성바이오로직스 (바이오 대장)
            "005380", # 현대차
            "000270", # 기아
            "068270", # 셀트리온
            "005490", # POSCO홀딩스 (철강/리튬)
            "035420", # NAVER
            "035720", # 카카오
            "006400", # 삼성SDI
            "051910", # LG화학
            "105560", # KB금융 (금융 대장)
            "055550", # 신한지주
            "003550", # LG
            "032830", # 삼성생명
            "015760", # 한국전력
            "034020", # 두산에너빌리티 (원전)
            "017670", # SK텔레콤
            "010140", # 삼성중공업 (조선)
        ]
        all_symbols.update(blue_chips)

        # 2. 거래량 상위 종목 (시장의 주도주)
        headers_vol = self.get_headers("FHPST01710000")
        params_vol = {
            "fid_cond_mrkt_div_code": "J", "fid_cond_scr_div_code": "20171", "fid_input_iscd": "0000",
            "fid_div_cls_code": "0", "fid_blng_cls_code": "0", "fid_trgt_cls_code": "11111111", 
            "fid_trgt_exls_cls_code": "000000", "fid_input_price_1": "", "fid_input_price_2": "", "fid_vol_cnt": "", "fid_input_date_1": ""
        }
        
        try:
            print("\n📡 거래량 상위 종목 필터링 중...")
            res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotations/volume-rank", headers=headers_vol, params=params_vol)
            data = res.json()
            if data['rt_cd'] == '0':
                count = 0
                for item in data['output'][:60]: # 60개 가져와서 거름
                    sym = item['mksc_shrn_iscd']
                    # API마다 이름 키값이 다를 수 있어 안전하게 가져오기
                    name = item.get('hts_kor_isnm') or item.get('stck_shrn_isnm') or ""
                    
                    if sym[0].isdigit(): # 숫자 코드로 된 것만 (주식)
                        # [수정] self.is_dirty_stock 호출
                        if self.is_dirty_stock(name):
                            pass
                        else:
                            all_symbols.add(sym)
                            count += 1
                print(f"   👉 거래량 상위에서 {count}개 종목 선정 완료")
        except Exception as e:
            print(f"   ⚠️ 거래량 순위 에러: {e}")

        # 3. 급등주 스캔
        headers_up = self.get_headers("FHPST01700000")
        params_up = {
            "fid_cond_mrkt_div_code": "J", "fid_cond_scr_div_code": "20170", "fid_input_iscd": "0000",
            "fid_rank_sort_cls_code": "0", "fid_input_cnt_1": "0", "fid_prc_cls_code": "1", "fid_input_price_1": "", "fid_input_price_2": "",
            "fid_vol_cnt": "", "fid_trgt_cls_code": "11111111", "fid_trgt_exls_cls_code": "000000"
        }
        
        try:
            print("📡 급등주 필터링 중...")
            res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/ranking/fluctuation", headers=headers_up, params=params_up)
            data = res.json()
            if data['rt_cd'] == '0':
                count = 0
                for item in data['output'][:60]:
                    sym = item['mksc_shrn_iscd']
                    name = item.get('hts_kor_isnm') or item.get('stck_shrn_isnm') or ""
                    
                    if sym[0].isdigit():
                        # [수정] self.is_dirty_stock 호출
                        if self.is_dirty_stock(name):
                            pass
                        else:
                            all_symbols.add(sym)
                            count += 1
                print(f"   👉 급등주에서 {count}개 종목 선정 완료")
        except Exception as e:
            print(f"   ⚠️ 급등주 에러: {e}")

        final_list = list(all_symbols)
        print(f"✅ 최종 감시 대상: 총 {len(final_list)}개 종목 확보!")
        return final_list

    def fetch_ohlcv(self, symbol, timeframe='3m', count=100):
        """
        [핵심 수정] 분봉 데이터 조회 전략
        1순위: 한국투자증권(KIS) 3분봉
        2순위: 실패 시 야후파이낸스 5분봉 (일봉 사용 절대 금지)
        """
        # 1. KIS API 시도
        headers = self.get_headers("FHKST03010200")
        headers["content-type"] = "application/json; charset=utf-8"
        
        # [시간 파라미터] 공란으로 두면 '가장 최근' 데이터를 줍니다.
        # (이게 안 되면 장 운영 시간이 아니거나 권한 문제)
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": symbol,
            "fid_etc_cls_code": "",
            "fid_pw_data_inum_2": "1",
            "fid_input_hour_1": "" 
        }
        
        try:
            url = f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
            res = requests.get(url, headers=headers, params=params)
            data = res.json()
            
            if data['rt_cd'] == '0' and data['output2']:
                # KIS 성공
                return pd.DataFrame(data['output2'])
            else:
                # KIS 실패 -> 바로 야후 파이낸스로 전환
                print(f"   ⚠️ KIS 분봉 실패({symbol}). 야후 파이낸스 연결 시도...")
                return self.fetch_from_yfinance(symbol)

        except Exception as e:
            print(f"   ❌ KIS 에러: {e}. 야후 파이낸스 연결 시도...")
            return self.fetch_from_yfinance(symbol)

    def fetch_from_yfinance(self, symbol):
        """
        [구원투수] 야후 파이낸스에서 분봉 데이터 긴급 공수
        """
        try:
            ks_ticker = f"{symbol}.KS"
            kq_ticker = f"{symbol}.KQ"
            # 최근 5일치, 5분봉 데이터 다운로드
            KS_ticker = yf.download(ks_ticker, period="5d", interval="5m", progress=False)
            KQ_ticker = yf.download(kq_ticker, period="5d", interval="5m", progress=False)

            if len(KS_ticker) > 10:
                data = KS_ticker
            elif len(KQ_ticker) > 10:
                data = KQ_ticker
            else:
                data = []
            
            
            if len(data) > 10:
                df = pd.DataFrame()
                # 야후 데이터 -> KIS 데이터 포맷으로 변환 (AI가 못 알아채게 위장)
                # Open->stck_oprc, High->stck_hgpr ...
                df['stck_oprc'] = data['Open'].astype(str) # 문자열로 변환 (KIS 포맷 맞춤)
                df['stck_hgpr'] = data['High'].astype(str)
                df['stck_lwpr'] = data['Low'].astype(str)
                df['stck_prpr'] = data['Close'].astype(str)
                df['cntg_vol'] = data['Volume'].astype(str)
                
                # 최신순 정렬 (야후는 과거순이므로 뒤집어야 KIS와 같아짐)
                df = df.iloc[::-1].reset_index(drop=True)
                
                print(f"   ✅ [Yahoo] {symbol} 분봉 확보 성공!")
                return df
            else:
                return None
        except Exception as e:
            print(f"   ❌ 야후 데이터 실패: {e}")
            return None
        
    def get_stock_name(self, symbol):
        """
        [종목명 조회 - 최종 수정]
        기존 '현재가 조회(inquire-price)' 대신 '상품정보조회(search-stock-info)' API를 사용하여
        종목명을 확실하게 가져옵니다.
        """
        # 1. 캐시(미리 저장된 이름) 확인 (API 절약)
        if hasattr(self, 'name_cache') and symbol in self.name_cache:
            return self.name_cache[symbol]

        # 2. 상품 기본정보 조회 API (CTPF1002R)
        # 이 API는 가격이 아니라 종목 정보를 전문으로 다룹니다.
        tr_id = "CTPF1002R"
        url = f"{URL_BASE}/uapi/domestic-stock/v1/quotations/search-stock-info"
        
        headers = self.get_headers(tr_id)
        params = {
            "PRDT_TYPE_CD": "300", # 300: 주식
            "PDNO": symbol         # 종목번호
        }
        
        try:
            # 0.5초 대기 (과부하 방지)
            time.sleep(0.5)
            
            res = requests.get(url, headers=headers, params=params)
            data = res.json()
            
            if data['rt_cd'] == '0':
                # search-stock-info API의 응답 구조: output -> prdt_name
                return data['output']['prdt_name']
            else:
                # print(f"   ⚠️ 이름 조회 실패({symbol}): {data.get('msg1')}")
                return data # 실패하면 코드 반환

        except Exception as e:
            print(f"   ❌ 종목명 에러({symbol}): {e}")
            return symbol

    def get_all_balance(self):
        self.is_vts = "vts" in URL_BASE
        """
        [현금 잔고 조회 - 최종 수정]
        모의투자(VTS)에서 PDNO(종목코드)를 비워두면 '주문가능현금(output)'을 안 주는 버그 해결.
        '005930(삼성전자)'를 더미로 넣어서 정확한 현금 데이터를 받아옵니다.
        """
        # 환경 분기
        if self.is_vts:
            # [모의투자 전용]
            tr_id = "VTTC8434R"
            url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"
            
            # [핵심 수정] PDNO에 "005930"을 넣어줌 (빈카니면 output을 안 줌)
            params = {
                "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "AFHR_FLPR_YN": "N", "OFL_YN": "N", 
                "INQR_DVSN": "02", "UNPR_DVSN": "01", "UNPR_DVSN_VIEW_YN": "Y",
                "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", 
                "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
            }
        else:
            # [실전투자 전용]
            tr_id = "TTTC8434R"
            url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"
            # 실전용 파라미터
            params = {
                "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "AFHR_FLPR_YN": "N", "OFL_YN": "N", 
                "INQR_DVSN": "02", "UNPR_DVSN": "01", "UNPR_DVSN_VIEW_YN": "Y", 
                "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", 
                "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
            }

        headers = self.get_headers(tr_id)
        try:
            time.sleep(0.5) # 호출 제한 방지
            res = requests.get(url, headers=headers, params=params)
            data = res.json()
            
            if data['rt_cd'] != '0':
                print(f"⚠️ 현금 잔고 조회 에러: {data.get('msg1')}")
                
            return data
            
        except Exception as e:
            print(f"❌ 현금 잔고 조회 실패: {e}")
            return None
        
    def get_balance(self):
        self.is_vts = "vts" in URL_BASE
        """
        [현금 잔고 조회 - 최종 수정]
        모의투자(VTS)에서 PDNO(종목코드)를 비워두면 '주문가능현금(output)'을 안 주는 버그 해결.
        '005930(삼성전자)'를 더미로 넣어서 정확한 현금 데이터를 받아옵니다.
        """
        # 환경 분기
        if self.is_vts:
            # [모의투자 전용]
            tr_id = "VTTC8908R"
            url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
            
            # [핵심 수정] PDNO에 "005930"을 넣어줌 (빈카니면 output을 안 줌)
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
            # [실전투자 전용]
            tr_id = "TTTC8434R"
            url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
            # 실전용 파라미터
            params = {
                "CANO": ACC_NO,
                "ACNT_PRDT_CD": "01",
                "PDNO": "005930",
                "ORD_UNPR": "65500",
                "ORD_DVSN": "01",
                "CMA_EVLU_AMT_ICLD_YN": "Y",
                "OVRS_ICLD_YN": "Y"
            }

        headers = self.get_headers(tr_id)
        try:
            time.sleep(0.5) # 호출 제한 방지
            res = requests.get(url, headers=headers, params=params)
            data = res.json()
            
            if data['rt_cd'] != '0':
                print(f"⚠️ 현금 잔고 조회 에러: {data.get('msg1')}")
                
            return data
            
        except Exception as e:
            print(f"❌ 현금 잔고 조회 실패: {e}")
            return None

    def get_my_stocks(self):
        """
        [잔고 조회 최종 수정판 v3]
        - 모의투자(VTS) 호출 시 'AFHR_FLPR_YN' 파라미터 완전 제거
        """
        # 1. 환경 분기 (모의투자 vs 실전투자)
        if "vts" in URL_BASE:
            # [모의투자] 주문가능조회 (VTTC8434R)
            tr_id = "VTTC8434R" 
            url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"
            
            # 모의투자용 파라미터 (여기에 AFHR_FLPR_YN이 절대 있으면 안 됩니다!)
            params = {
                "CANO": ACC_NO, 
                "ACNT_PRDT_CD": "01", 
                "AFHR_FLPR_YN": "N", 
                "OFL_YN": "N", 
                "INQR_DVSN": "02", 
                "UNPR_DVSN": "01", 
                "FUND_STTL_ICLD_YN": "N", 
                "FNCG_AMT_AUTO_RDPT_YN": "N", 
                "PRCS_DVSN": "00", 
                "CTX_AREA_FK100": "", 
                "CTX_AREA_NK100": ""
            }
        else:
            # [실전투자] 주식잔고조회 (TTTC8404R)
            tr_id = "TTTC8404R"
            url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"
            
            # 실전투자용 파라미터 (여기는 AFHR_FLPR_YN이 있어야 함)
            params = {
                "CANO": ACC_NO, 
                "ACNT_PRDT_CD": "01", 
                "AFHR_FLPR_YN": "N", 
                "OFL_YN": "N", 
                "INQR_DVSN": "02", 
                "UNPR_DVSN": "01", 
                "FUND_STTL_ICLD_YN": "N", 
                "FNCG_AMT_AUTO_RDPT_YN": "N", 
                "PRCS_DVSN": "00", 
                "CTX_AREA_FK100": "", 
                "CTX_AREA_NK100": ""
            }

        headers = self.get_headers(tr_id)
        stock_dict = {}
        
        try:
            # [속도 제한 방지]
            time.sleep(0.2)
            
            res = requests.get(url, headers=headers, params=params)
            data = res.json()
            
            if data['rt_cd'] == '0':
                if 'output1' in data:
                    for item in data['output1']:
                        # 보유수량 파싱 (모의: ord_psbl_qty / 실전: hldg_qty)
                        qty = int(item.get('hldg_qty') or item.get('ord_psbl_qty') or 0)
                        
                        if qty > 0:
                            symbol = item['pdno']
                            buy_price = float(item.get('pchs_avg_pric') or 0)
                            current_price = int(item.get('prpr') or 0)
                            
                            stock_dict[symbol] = {
                            'qty': qty, 
                            'buy_price': buy_price, 
                            'current_price': current_price,
                            'name': item['prdt_name'] 
                            }
            else:
                # ❌ 실패 시 로직 (else 블록으로 이동됨)
                print(f"⚠️ 잔고 조회 실패: {data.get('msg1')}")
                
        except Exception as e:
            print(f"❌ 잔고 조회 에러: {e}")
        return stock_dict

    def get_current_price(self, symbol):
        headers = self.get_headers("FHKST01010100")
        params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": symbol}
        try:
            res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-price", headers=headers, params=params)
            return int(res.json()['output']['stck_prpr'])
        except:
            return 0

    def buy_market_order(self, symbol, qty):

        time.sleep(1.0)

        tr_id = "VTTC0802U" if "vts" in URL_BASE else "TTTC0802U"
        headers = self.get_headers(tr_id)

        # [안전 장치] 정수형(int)으로 강제 변환
        qty = int(qty)
        
        # [확인용 로그] 실제로 몇 주를 요청하는지 눈으로 확인!
        print(f"📉 [매수 요청] {symbol} 종목을 {qty}주 시장가로 매수합니다.")

        params = {
            "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "PDNO": symbol, "ORD_DVSN": "01", "ORD_QTY": str(qty), "ORD_UNPR": "0"
        }
        res = requests.post(f"{URL_BASE}/uapi/domestic-stock/v1/trading/order-cash", headers=headers, data=json.dumps(params))
        result = res.json()
        if result['rt_cd'] == '0':
            print(f"   ✅ 매수 주문 성공! (주문번호: {result['output']['ODNO']})")
            return {'status': 'success'}
        else:
            print(f"   ❌ 매수 주문 실패: {result['msg1']}")
            return {'status': 'fail'}

    def sell_market_order(self, symbol, qty): 
        tr_id = "VTTC0801U" if "vts" in URL_BASE else "TTTC0801U"
        headers = self.get_headers(tr_id)
        
        # [안전 장치] 정수형(int)으로 강제 변환
        qty = int(qty)
        
        # [확인용 로그] 실제로 몇 주를 요청하는지 눈으로 확인!
        print(f"📉 [매도 요청] {symbol} 종목을 {qty}주 시장가로 매도합니다.")

        params = {
            "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "PDNO": symbol, "ORD_DVSN": "01", 
            "ORD_QTY": str(qty), "ORD_UNPR": "0"
        }
        res = requests.post(f"{URL_BASE}/uapi/domestic-stock/v1/trading/order-cash", headers=headers, data=json.dumps(params))
        
        result = res.json()
        if result['rt_cd'] == '0':
            print(f"   ✅ 매도 주문 성공! (주문번호: {result['output']['ODNO']})")
            return {'status': 'success'}
        else:
            print(f"   ❌ 매도 주문 실패: {result['msg1']}")
            return {'status': 'fail'}

    # kis_api.py (보강된 전량 매도 로직)
    def sell_all_holdings(self):
        """보유한 모든 종목을 시장가로 즉시 전량 매도"""
        stocks = self.get_my_stocks()
        if not stocks:
            print("📭 매도할 보유 종목이 없습니다.")
            return

        print(f"🧹 총 {len(stocks)}개 종목 전량 청산을 시작합니다.")
        for sym, info in stocks.items():
            qty = info['qty']
            print(f"   📤 [{sym}] {qty}주 일괄 매도 중...")
            self.sell_market_order(sym, qty)
            time.sleep(0.2) # API 과부하 방지

    def get_live_ranking(self, count=30):
        return self.get_top_100()[:count]

    def create_dummy_data(self):
        # 최후의 수단: 가상 데이터 (시스템 멈춤 방지용)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300, freq='3min')
        prices = [70000]
        for _ in range(299): prices.append(prices[-1] * (1 + np.random.uniform(-0.005, 0.005)))
        return pd.DataFrame({'stck_prpr': prices, 'stck_oprc': prices, 'stck_hgpr': prices, 'stck_lwpr': prices, 'cntg_vol': np.random.randint(1000, 50000, 300)})

    def cancel_all_unfilled_orders(self):
        """
        [청소부] 미체결된 주문을 모두 찾아서 일괄 취소합니다.
        (self.is_vts 에러 방지 수정판)
        """
        # [수정] 클래스 변수 대신 여기서 직접 확인 (에러 방지)
        is_vts_mode = "vts" in URL_BASE

        # 1. 미체결 내역 조회
        tr_id = "VTTC8001R" if is_vts_mode else "TTTC8001R"
        url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        
        headers = self.get_headers(tr_id)
        params = {
            "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "INQR_STRT_DT": "20240101", "INQR_END_DT": "20301231",
            "SLL_BUY_DVSN_CD": "00", "INQR_DVSN": "00", "PDNO": "", "CCLD_DVSN": "02", # 02: 미체결만
            "ORD_GNO_BRNO": "", "ODNO": "", "INQR_DVSN_3": "00", "INQR_DVSN_1": "", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
        }

        try:
            res = requests.get(url, headers=headers, params=params)
            data = res.json()
            
            unfilled_list = []
            if data['rt_cd'] == '0' and 'output1' in data:
                unfilled_list = data['output1']
            
            if len(unfilled_list) == 0:
                # 미체결 없음 -> 조용히 리턴
                return

            print(f"\n🧹 [청소] 미체결 주문 {len(unfilled_list)}건 발견! 일괄 취소를 진행합니다.")
            msg = f"🧹 [청소] 미체결 주문 {len(unfilled_list)}건 발견! 일괄 취소를 진행합니다."
            color = 0x00ff00
            send_message("🧹 미체결 정산", msg, color)

            # 2. 발견된 주문 취소 실행
            cancel_tr_id = "VTTC0803U" if is_vts_mode else "TTTC0803U"
            cancel_url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/order-rvsecncl"
            
            for item in unfilled_list:
                odno = item['odno'] # 원주문번호
                org_no = item['ord_gno_brno'] 
                if not org_no: org_no = "02070" 
                
                cancel_headers = self.get_headers(cancel_tr_id)
                
                cancel_params = {
                    "CANO": ACC_NO, "ACNT_PRDT_CD": "01", 
                    "KRX_FWDG_ORD_ORGNO": "", "ORGN_ODNO": odno, 
                    "ORD_DVSN": "00", 
                    "RVSE_CNCL_DVSN_CD": "02", # 전량 취소
                    "ORD_QTY": "0", 
                    "ORD_UNPR": "0", "QTY_ALL_ORD_YN": "Y" 
                }
                
                res = requests.post(cancel_url, headers=cancel_headers, data=json.dumps(cancel_params))
                if res.json()['rt_cd'] == '0':
                    print(f"   🗑️ 주문취소 성공: {item['prdt_name']} (주문번호: {odno})")
                else:
                    print(f"   ⚠️ 주문취소 실패: {res.json()['msg1']}")
                
                time.sleep(0.2)

        except Exception as e:
            print(f"❌ 미체결 정리 중 오류: {e}")

    def current_unfilled_orders(self):
        """
        [청소부] 미체결된 주문을 모두 찾아서 일괄 취소합니다.
        (self.is_vts 에러 방지 수정판)
        """
        # [수정] 클래스 변수 대신 여기서 직접 확인 (에러 방지)
        is_vts_mode = "vts" in URL_BASE

        # 1. 미체결 내역 조회
        tr_id = "VTTC8001R" if is_vts_mode else "TTTC8001R"
        url = f"{URL_BASE}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        
        headers = self.get_headers(tr_id)
        params = {
            "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "INQR_STRT_DT": "20240101", "INQR_END_DT": "20301231",
            "SLL_BUY_DVSN_CD": "00", "INQR_DVSN": "00", "PDNO": "", "CCLD_DVSN": "02", # 02: 미체결만
            "ORD_GNO_BRNO": "", "ODNO": "", "INQR_DVSN_3": "00", "INQR_DVSN_1": "", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
        }

        try:
            res = requests.get(url, headers=headers, params=params)
            data = res.json()
            
            unfilled_list = []
            if data['rt_cd'] == '0' and 'output1' in data:
                unfilled_list = data['output1']
            
            if len(unfilled_list) == 0 or not unfilled_list:
                # 미체결 없음 -> 0을 리턴턴
                return 0

            return len(unfilled_list)

        except Exception as e:
            print(f"❌ 미체결 확보 중 오류: {e}")