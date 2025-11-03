import time
import os
import sys
import datetime 
from google import genai
from google.genai.types import GenerateVideosConfig
from google.cloud import storage  # GCS 및 서명된 URL 생성을 위해 필요
from dotenv import load_dotenv
from urllib.parse import urlparse  # gs:// URI 파싱을 위해 필요

# .env 파일에서 환경 변수 로드
load_dotenv()

# GCS 클라이언트 초기화
# gcloud auth application-default login 명령어로 인증된 계정을 사용합니다.
try:
    storage_client = storage.Client()
except Exception as e:
    print(f"GCS 클라이언트 초기화 실패: {e}")
    print("GCP 인증(gcloud auth application-default login)이 올바르게 되었는지 확인")
    sys.exit(1)

def generate_signed_url(gcs_uri: str, expiration_minutes: int = 15) -> str:
    """
    (추가된 부분)
    'gs://bucket/object' URI를 브라우저 접속용 서명된 URL로 변환합니다.
    이것이 "버킷에서 데이터를 꺼내오는" 핵심 로직입니다.
    """
    
     # 최대 50분까지만 허용
    if expiration_minutes < 1:
        expiration_minutes = 1
    elif expiration_minutes > 50:
        expiration_minutes = 50

    try:
        # 1. gs:// URI를 버킷 이름과 파일 경로로 분리
        parsed_url = urlparse(gcs_uri)
        bucket_name = parsed_url.netloc
        object_name = parsed_url.path.lstrip('/')

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        print(f"\n'{gcs_uri}'에 대한 서명된 URL 생성 중...")
        
        # 2. 15분간 유효한 임시 URL 생성 (v4 방식)
        url = blob.generate_signed_url(
            version="v4",
            expiration= datetime.timedelta(minutes=expiration_minutes),  # 안전하게 timedelta 사용,
            method="GET",
        )
        return url
    except Exception as e:
        print(f"서명된 URL 생성 실패: {e}")
        print("GCS 버킷 접근 권한 또는 '서비스 계정 토큰 생성자' 역할이 있는지 확인하세요.")
        raise

def main():
    # .env 파일에서 GCS 경로 불러오기
    output_gcs_uri = os.environ.get("OUTPUT_GCS_URI")
    if not output_gcs_uri or not output_gcs_uri.startswith("gs://"):
        print(".env 파일에 'OUTPUT_GCS_URI'가 올바르게 설정되지 않았습니다. (예: gs://my-bucket/videos/)")
        return

    # API 키 설정(genai.configure) 대신 Vertex AI 인증(gcloud) 사용
    '''
    추후에 이 부분은 프론트 입력으로 대체 될 것임.
    '''
    prompt = """A close up of two people staring at a cryptic drawing on a wall, torchlight flickering.
A man murmurs, 'This must be it. That's the secret code.' The woman looks at him and whispering excitedly, 'What did you find?'"""
   
    try:
        # Vertex AI 인증을 사용하는 클라이언트 생성
        client = genai.Client()
        print(f"VEO 비디오 생성을 시작합니다... (Vertex AI 방식)")
        print(f"프롬프트: {prompt[:50]}...")
        print(f"저장 위치: {output_gcs_uri}")

        # GCS 설정(config) 블록 부활
        operation = client.models.generate_videos(
            model="veo-3.0-generate-001", 
            prompt=prompt,
            config=GenerateVideosConfig(
                aspect_ratio="16:9",        # 화면 피율 설정
                output_gcs_uri=output_gcs_uri,
                duration_seconds = 6      # 동영상 길이 제한 (5초)
            ),
        )

        print("\n작업 대기 중... (완료까지 몇 분 소요됩니다)")
        
        while not operation.done:
            time.sleep(15) 
            operation = client.operations.get(operation)
            state_name = operation.metadata.state.name if operation.metadata else '알 수 없음'
            print(f"... 작업 상태: {state_name}")

        if operation.error:
            # 안전하게 에러 메시지 추출
            if isinstance(operation.error, dict):
                error_message = operation.error.get("message", "Unknown error")
            else:
                error_message = getattr(operation.error, "message", str(operation.error))

            print(f"\n비디오 생성 실패: {error_message}")
            return  # 이 return이 있으면, 아래에서 error_message를 다시 쓰지 않음



        # GCS URI를 응답으로 받음
        if operation.response:
            gcs_uri = operation.result.generated_videos[0].video.uri
            print(f"\n비디오 생성 완료! GCS URI: {gcs_uri}")
            
            '''
            이 부분은 프론트에 응답으로 뿌릴거
            '''
            
            
            # (추가된 부분) 
            # GCS URI를 서명된 URL(https://...)로 변환
            signed_url = generate_signed_url(gcs_uri)
            
            print("\n" + "="*50)
            print("성공! 이 URL을 프론트엔드 <video> 태그에 사용하세요.")
            print("(이 URL은 15분간 유효합니다)")
            print(f"\n{signed_url}\n")
            print("="*50)

    except Exception as e:
        print(f"\n 스크립트 실행 중 예외 발생: {e}")

if __name__ == "__main__":
    main()

