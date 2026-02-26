# collector.py
import torch
import pandas as pd
import numpy as np
from config import DEVICE, SEQ_LEN # config.py에 SEQ_LEN이 있어야 합니다 (보통 10)

def preprocess_data(api, symbol):
    """
    [데이터 수집 및 전처리기 v2]
    실시간 매매 시 사용되는 함수입니다.
    API에서 데이터를 가져와서, AI가 학습한 것과 똑같은 형태(10개 피쳐)로 가공합니다.
    """
    # 1. API 데이터 조회
    # [중요] 보조지표(20일 이평선, RSI 14일)를 계산하려면 
    # SEQ_LEN(10개)보다 훨씬 많은 과거 데이터가 필요합니다.
    # 따라서 넉넉하게 50~60개를 요청합니다.
    raw_df = api.fetch_ohlcv(symbol, timeframe='3m', count=60)
    
    # 2. 데이터 유효성 검사
    # 최소 30개는 있어야 보조지표 계산 후 NaN을 지워도 데이터가 남습니다.
    if raw_df is None or len(raw_df) < 30:
        return None

    try:
        # 3. 데이터 복사 및 타입 변환
        df = raw_df.copy()
        cols = ['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'cntg_vol']
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # [중요] 시간 정렬: 과거 -> 현재 순서로 맞춤
        # API는 보통 최신순(역순)으로 주므로 뒤집어야 함
        df = df.iloc[::-1].reset_index(drop=True)

        # ---------------------------------------------------------
        # [4. Feature Engineering] train.py와 동일한 로직 적용
        # ---------------------------------------------------------
        # (1) 이동평균 & 이격도 (가격이 평균보다 얼마나 비싼가?)
        df['ma5'] = df['stck_prpr'].rolling(window=5).mean()
        df['ma20'] = df['stck_prpr'].rolling(window=20).mean()
        
        # 분모 0 방지 (+ 1e-8)
        df['disp5'] = df['stck_prpr'] / (df['ma5'] + 1e-8)
        df['disp20'] = df['stck_prpr'] / (df['ma20'] + 1e-8)

        # (2) RSI (상대강도지수)
        delta = df['stck_prpr'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-8)
        df['rsi'] = 100 - (100 / (1 + rs))

        # (3) 로그 수익률 & 거래량 변화율
        df['log_ret'] = np.log(df['stck_prpr'] / df['stck_prpr'].shift(1))
        df['vol_chg'] = df['cntg_vol'] / (df['cntg_vol'].shift(1) + 1e-8)

        # NaN 제거 (지표 계산 초반 데이터 삭제)
        df = df.dropna().reset_index(drop=True)

        # ---------------------------------------------------------

        # 5. 데이터 길이 재확인
        # 전처리 후에도 우리가 필요한 길이(SEQ_LEN=10)보다 적으면 예측 불가
        if len(df) < SEQ_LEN:
            return None

        # 6. 마지막 SEQ_LEN(10개)만 자르기
        # AI는 '가장 최근 10개'를 보고 미래를 예측합니다.
        target_df = df.tail(SEQ_LEN)

        # 7. 10개 피쳐 선택 (순서 중요! train.py와 같아야 함)
        features = ['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'cntg_vol', 
                    'disp5', 'disp20', 'rsi', 'log_ret', 'vol_chg']
        
        data = target_df[features].values.astype(float)

        # 8. 정규화 (MinMax Scaling)
        # 딥러닝 모델은 0~1 사이의 숫자를 좋아합니다.
        # 현재 보고 있는 10개 데이터 내에서의 최대/최소를 기준으로 정규화합니다.
        min_vals = data.min(axis=0)
        max_vals = data.max(axis=0)
        ranges = max_vals - min_vals
        ranges[ranges == 0] = 1e-8 # 0으로 나누기 방지
        
        scaled_data = (data - min_vals) / ranges

        # 9. 텐서 변환 (Batch 차원 추가)
        # 형태: (Batch=1, Seq=10, Feature=10)
        input_tensor = torch.FloatTensor(scaled_data).unsqueeze(0).to(DEVICE)
        
        return input_tensor

    except Exception as e:
        # print(f"⚠️ 데이터 전처리 실패 ({symbol}): {e}")
        return None