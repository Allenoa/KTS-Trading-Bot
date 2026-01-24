# model.py
import torch
import torch.nn as nn

class ScalpingLSTM(nn.Module):
    def __init__(self, input_size=5, hidden_size=32, num_layers=2, output_size=1):
        """
        Args:
            input_size: 입력 데이터의 특징 개수 (현재가, 시가, 고가, 저가, 거래량 = 5)
            hidden_size: AI의 두뇌 용량 (기본 32)
            num_layers: LSTM 층의 깊이 (기본 2)
            output_size: 출력 결과의 개수 (예측할 가격 = 1)
        """
        super(ScalpingLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # LSTM 레이어 설정
        # batch_first=True: 데이터 순서가 (배치, 시간, 특징) 순서임을 명시
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)

        # 완전 연결 레이어 (결과 출력용)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # 1. 초기 은닉 상태와 셀 상태를 0으로 초기화 (GPU/CPU 자동 대응)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)

        # 2. LSTM 순전파
        # out 형태: (batch_size, seq_len, hidden_size)
        out, _ = self.lstm(x, (h0, c0))

        # 3. 마지막 시간대(Time Step)의 결과만 가져오기
        # 우리는 '다음 날' 딱 하루의 가격만 궁금하기 때문
        out = self.fc(out[:, -1, :])
        
        return out