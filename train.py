# train.py
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
import glob
from model import ScalpingLSTM
from config import DEVICE

# [설정]
SEQ_LEN = 10     # 10개를 보고
PREDICT_LEN = 1  # 1개를 예측
BATCH_SIZE = 32  # 배치 사이즈 살짝 증가
EPOCHS = 100     # 학습 횟수 증가

def add_advanced_features(df):
    """
    [Feature Engineering] 
    AI가 시장을 더 잘 이해하도록 보조지표 5개를 추가합니다.
    총 10개 피쳐: [종가, 시가, 고가, 저가, 거래량] + [이격도5, 이격도20, RSI, 변동성, 거래량변화]
    """
    df = df.copy()
    
    # 0. 기본 전처리 (숫자 변환)
    cols = ['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'cntg_vol']
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # [중요] 시간 순서 정렬 (과거 -> 미래)
    # API 데이터는 보통 역순(최신이 위)이므로 뒤집어줘야 함
    df = df.iloc[::-1].reset_index(drop=True)

    # 1. 이동평균 이격도 (Disparity)
    # 가격이 평균보다 얼마나 높냐/낮냐 (1.05 = 5% 비쌈)
    df['ma5'] = df['stck_prpr'].rolling(window=5).mean()
    df['ma20'] = df['stck_prpr'].rolling(window=20).mean()
    df['disp5'] = df['stck_prpr'] / (df['ma5'] + 1e-8)
    df['disp20'] = df['stck_prpr'] / (df['ma20'] + 1e-8)

    # 2. RSI (상대강도지수)
    delta = df['stck_prpr'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-8)
    df['rsi'] = 100 - (100 / (1 + rs))

    # 3. 로그 수익률 (변동성)
    df['log_ret'] = np.log(df['stck_prpr'] / df['stck_prpr'].shift(1))

    # 4. 거래량 변화율
    df['vol_chg'] = df['cntg_vol'] / (df['cntg_vol'].shift(1) + 1e-8)

    # NaN 제거 (지표 계산하느라 앞부분 20개 정도 빔)
    df = df.dropna().reset_index(drop=True)
    
    return df

class StockDataset(Dataset):
    def __init__(self, file_paths, seq_len=SEQ_LEN):
        self.samples = []
        
        print(f"📂 학습 데이터 로딩 및 피쳐 생성 중... (파일 {len(file_paths)}개)")
        
        for path in file_paths:
            try:
                raw_df = pd.read_csv(path)
                if len(raw_df) < 30: continue # 데이터 너무 적으면 패스

                # ★ 보조지표 추가 (Feature Engineering)
                df = add_advanced_features(raw_df)
                
                if len(df) < seq_len + 1: continue

                # 사용할 컬럼 10개 선정
                features = ['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'cntg_vol', 
                            'disp5', 'disp20', 'rsi', 'log_ret', 'vol_chg']
                
                data = df[features].values
                
                # 정규화 (MinMax Scaling 0~1)
                # 각 컬럼별로 최대/최소 구해서 정규화
                min_vals = data.min(axis=0)
                max_vals = data.max(axis=0)
                
                # 분모 0 방지
                ranges = max_vals - min_vals
                ranges[ranges == 0] = 1e-8
                
                scaled_data = (data - min_vals) / ranges

                # 시퀀스 데이터 생성
                for i in range(len(scaled_data) - seq_len):
                    x = scaled_data[i : i+seq_len]      # 10일치 데이터 (10개 컬럼)
                    # 예측 목표: 다음날의 '종가(Close)' (0번째 컬럼)
                    y = scaled_data[i+seq_len][0]       
                    
                    self.samples.append((
                        torch.FloatTensor(x), 
                        torch.FloatTensor([y])
                    ))
                    
            except Exception as e:
                # print(f"⚠️ 에러({path}): {e}")
                continue

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]

def train():
    print(f"🔥 학습 시작 (Device: {DEVICE})")
    
    file_list = glob.glob("data/raw/*.csv")
    if not file_list:
        print("❌ 'data/raw' 폴더에 CSV 파일이 없습니다.")
        return

    dataset = StockDataset(file_list)
    if len(dataset) == 0:
        print("⚠️ 학습 가능한 데이터가 없습니다.")
        return

    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    print(f"✅ 데이터셋 준비 완료! (총 샘플: {len(dataset)}개)")

    # [모델 생성] input_size=10 (피쳐 개수)
    model = ScalpingLSTM(input_size=10, hidden_size=64, num_layers=2, output_size=1, dropout=0.2).to(DEVICE)
    
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()

    model.train()
    
    for epoch in range(EPOCHS):
        total_loss = 0
        for x, y in dataloader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            
            optimizer.zero_grad()
            output = model(x)
            loss = criterion(output, y)
            
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        if (epoch+1) % 10 == 0:
            avg_loss = total_loss / len(dataloader)
            print(f"Epoch [{epoch+1}/{EPOCHS}] Loss: {avg_loss:.6f}")

    torch.save(model.state_dict(), "scalping_model.pth")
    print("🎉 학습 완료! 모델 저장됨: scalping_model.pth")

if __name__ == "__main__":
    train()