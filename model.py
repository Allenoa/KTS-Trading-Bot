# model.py
import torch
import torch.nn as nn

class ScalpingLSTM(nn.Module):
    def __init__(self, input_size=10, hidden_size=64, num_layers=2, output_size=1, dropout=0.2):
        """
        [모델 개선]
        - input_size: 5 -> 10 (보조지표 추가로 늘어남)
        - hidden_size: 32 -> 64 (두뇌 용량 증가)
        - dropout: 0.2 (과적합 방지, 20% 뉴런을 무작위로 끔)
        """
        super(ScalpingLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # LSTM 레이어 (Dropout 적용)
        self.lstm = nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers, 
            batch_first=True, 
            dropout=dropout
        )

        # 완전 연결 레이어
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)

        out, _ = self.lstm(x, (h0, c0))
        
        # 마지막 시간대의 결과만 사용
        out = self.fc(out[:, -1, :])
        return out