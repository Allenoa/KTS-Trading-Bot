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

# [설정] 데이터가 적어도 학습되도록 설정값 조정
SEQ_LEN = 10  # 과거 10개를 보고 다음을 예측
BATCH_SIZE = 16
EPOCHS = 50

class StockDataset(Dataset):
    def __init__(self, file_paths, seq_len=SEQ_LEN):
        self.samples = []
        self.seq_len = seq_len
        
        print(f"📂 학습 데이터 로딩 중... (파일 {len(file_paths)}개 감지)")
        
        for path in file_paths:
            try:
                # 1. CSV 읽기
                df = pd.read_csv(path)
                
                # 데이터가 텅 비었거나 너무 짧으면 패스
                if len(df) < seq_len + 1:
                    continue

                # 문자열을 숫자로 강제 변환 (에러 방지)
                cols = ['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'cntg_vol']
                for col in cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # NaN(빈값) 제거
                df = df.dropna()

                # 시간 순서 정렬 (일봉은 역순으로 들어오므로 뒤집기)
                df = df.iloc[::-1].reset_index(drop=True)

                # 4. 정규화 (Normalization)
                price_data = df[['stck_prpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr']].values
                volume_data = df[['cntg_vol']].values
                
                price_max = price_data.max()
                price_min = price_data.min()
                vol_max = volume_data.max()
                
                if price_max == price_min or vol_max == 0:
                    continue

                scaled_price = (price_data - price_min) / (price_max - price_min + 1e-8)
                scaled_vol = volume_data / (vol_max + 1e-8)
                
                # 합치기 (5개 피쳐)
                data = np.hstack([scaled_price, scaled_vol])
                
                # 5. 시퀀스 데이터 생성
                for i in range(len(data) - seq_len):
                    x = data[i : i+seq_len]      # 과거 10일치
                    y = data[i+seq_len][0]       # 다음날 종가(현재가) 예측
                    
                    self.samples.append((
                        torch.FloatTensor(x), 
                        torch.FloatTensor([y])
                    ))
                    
            except Exception as e:
                print(f"⚠️ 데이터 처리 중 에러 ({path}): {e}")
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
        print("⚠️ 유효한 학습 데이터가 없습니다. (데이터 부족 또는 형식 오류)")
        return

    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    print(f"✅ 데이터셋 준비 완료! (총 샘플 수: {len(dataset)}개)")

    # [핵심 수정] 변수명 지정 없이 순서대로 값만 전달 (위치 인자 사용)
    # ScalpingLSTM(input_size, hidden_size, num_layers, output_size) 순서라고 가정
    # 에러가 나지 않게 가장 일반적인 순서로 값을 넣습니다.
    # (입력차원: 5, 은닉층: 32, 레이어수: 2, 출력차원: 1)
    try:
        model = ScalpingLSTM(5, 32, 2, 1).to(DEVICE)
    except Exception as e:
        print(f"❌ 모델 초기화 에러: {e}")
        print("💡 model.py의 __init__ 함수 인자 순서를 확인해주세요.")
        return

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
    print("🎉 학습 완료! 'scalping_model.pth' 저장됨.")

if __name__ == "__main__":
    train()