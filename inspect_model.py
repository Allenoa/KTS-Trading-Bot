import torch
import os

# 파일 경로 (혹시 경로가 다르면 수정하세요)
MODEL_PATH = "scalping_model.pth"

def inspect():
    if not os.path.exists(MODEL_PATH):
        print(f"❌ 파일이 없습니다: {MODEL_PATH}")
        return

    print(f"📂 모델 파일 로딩 중: {MODEL_PATH}...")
    
    # 1. 파일 열기 (CPU로 로드)
    try:
        state_dict = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
    except Exception as e:
        print(f"❌ 파일 열기 실패: {e}")
        return

    print("\n🧠 [AI 모델 내부 구조 및 가중치 통계]")
    print("-" * 60)
    print(f"{'Layer Name (층 이름)':<30} | {'Shape (크기)':<20} | {'Mean (평균값)'}")
    print("-" * 60)

    # 2. 각 레이어(층) 별로 정보 출력
    for param_tensor in state_dict:
        # 텐서(행렬) 값 가져오기
        tensor_val = state_dict[param_tensor]
        
        # 이름, 크기(차원), 평균값 출력
        # 평균값이 0이 아니어야 학습이 된 것입니다.
        print(f"{param_tensor:<30} | {str(list(tensor_val.size())):<20} | {tensor_val.float().mean():.6f}")

    print("-" * 60)
    print("✅ 분석 완료. 'Mean' 값이 0.0이나 NaN이 아니면 정상입니다.")

if __name__ == "__main__":
    inspect()