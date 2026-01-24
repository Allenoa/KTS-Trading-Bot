import torch
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from config import DEVICE, WINDOW_SIZE

def preprocess_data(api, symbol):
    """
    [수정됨] API와 종목코드를 받아서 -> 실시간 데이터 조회 -> AI 입력용 텐서 변환
    """
    # 1. API를 통해 과거 데이터 조회 (3분봉, WINDOW_SIZE만큼)
    # fetch_ohlcv 함수는 우리가 kis_api.py에 만들어뒀습니다.
    raw_df = api.fetch_ohlcv(symbol, timeframe='3m', count=WINDOW_SIZE)
    
    # 2. 데이터 유효성 검사
    if raw_df is None or len(raw_df) < WINDOW_SIZE:
        # 데이터가 없거나 부족하면 None 반환 (매매 패스)
        return None

    try:
        # 3. 필요한 5가지 특성 추출 (종가, 시가, 고가, 저가, 거래량)
        # API가 주는 데이터의 컬럼명에 맞춰 추출
        features = raw_df[['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'cntg_vol']].values.astype(float)
        
        # 4. 정규화 (0~1 사이 값으로 변환)
        # 주의: 실전에서는 학습 때 사용한 Scaler를 저장해서 불러와야 정확하지만,
        # 간이용으로 여기서는 매번 새로 피팅합니다 (MinMax는 상대적이라 큰 문제 없음)
        scaler = MinMaxScaler()
        scaled_features = scaler.fit_transform(features)
        
        # 5. 최근 데이터만 잘라서 텐서로 변환
        # (Batch Size, Sequence Length, Input Size) -> (1, 30, 5)
        recent_data = scaled_features[-WINDOW_SIZE:]
        input_tensor = torch.FloatTensor(recent_data).unsqueeze(0).to(DEVICE)
        
        return input_tensor

    except Exception as e:
        print(f"⚠️ 전처리 중 에러 발생 ({symbol}): {e}")
        return None