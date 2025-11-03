import time
import os
import sys
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
    print(f"❌ GCS 클라이언트 초기화 실패: {e}")
    print("GCP 인증(gcloud auth application-default login)이 올바르게 되었는지 확인하세요.")
    sys.exit(1)


def generate_signed_url(gcs_uri: str, expiration_minutes: int = 15) -> str:
    """
    'gs://bucket/object' URI를 브라우저 접속용 서명된 URL로 변환합니다.
    """
    try:
        # 1. gs:// URI를 버킷 이름과 파일 경로로 분리
        parsed_url = urlparse(gcs_uri)
        bucket_name = parsed_url.netloc
        object_name = parsed_url.path.lstrip('/')

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        print(f"\n📄 '{gcs_uri}'에 대한 서명된 URL 생성 중...")

        # 2. 15분간 유효한 임시 URL 생성 (v4 방식)
        url = blob.generate_signed_url(
            version="v4",
            expiration=time.time() + (expiration_minutes * 60),
            method="GET",
        )
        return url
    except Exception as e:
        print(f"❌ 서명된 URL 생성 실패: {e}")
        print("GCS 버킷 접근 권한 또는 '서비스 계정 토큰 생성자' 역할이 있는지 확인하세요.")
        raise


def main():
    # .env 파일에서 GCS 경로 불러오기
    output_gcs_uri = os.environ.get("OUTPUT_GCS_URI")
    if not output_gcs_uri or not output_gcs_uri.startswith("gs://"):
        print("❌ .env 파일에 'OUTPUT_GCS_URI'가 올바르게 설정되지 않았습니다. (예: gs://my-bucket/videos/)")
        return

    # 사용자 스니펫에 있던 프롬프트 사용
    prompt = """A close up of two people staring at a cryptic drawing on a wall, torchlight flickering.
A man murmurs, 'This must be it. That's the secret code.' The woman looks at him and whispering excitedly, 'What did you find?'"""

    try:
        # Vertex AI 인증을 사용하므로 API 키가 필요 없습니다.
        client = genai.Client()
        print(f"🚀 VEO 비디오 생성을 시작합니다...")
        print(f"프롬프트: {prompt[:50]}...")
        print(f"저장 위치: {output_gcs_uri}")

        # 1. VEO API 호출 (Vertex AI 모델 사용)
        operation = client.models.generate_videos(
            model="veo-3.0-generate-001",
            prompt=prompt,
            config=GenerateVideosConfig(
                aspect_ratio="16:9",
                output_gcs_uri=output_gcs_uri,
            ),
        )

        print("\n⏳ 작업 대기 중... (완료까지 몇 분 정도 걸릴 수 있습니다)")

        # 2. 작업 완료 대기 (폴링)
        while not operation.done:
            time.sleep(15)  # 15초마다 상태 확인
            operation = client.operations.get(operation)
            state_name = operation.metadata.state.name if operation.metadata else '알 수 없음'
            print(f"... 작업 상태: {state_name}")

        if operation.error:
            print(f"\n❌ 비디오 생성 실패: {operation.error.message}")
            return

        # 3. GCS URI 결과 받기
        if operation.response:
            # VEO API는 'gs://...' URI를 반환합니다.
            gcs_uri = operation.result.generated_videos[0].video.uri
            print(f"\n✅ 비디오 생성 완료! GCS URI: {gcs_uri}")

            # 4. GCS URI를 서명된 URL(https://...)로 변환
            signed_url = generate_signed_url(gcs_uri)

            print("\n" + "="*50)
            print("🎉 성공! 아래 URL을 복사하여 웹 브라우저에서 비디오를 확인하세요.")
            print("(이 URL은 15분간 유효합니다)")
            print(f"\n{signed_url}\n")
            print("="*50)

    except Exception as e:
        print(f"\n❌ 스크립트 실행 중 예외 발생: {e}")


if __name__ == "__main__":
    main()

# # Python 코드

# import time
# from google import genai

# client = genai.Client()  # 여기에 API 키를 설정함
# prompt = """A close up of two people staring at a cryptic drawing on a wall, torchlight flickering.
# A man murmurs, 'This must be it. That's the secret code.' The woman looks at him and whispering excitedly, 'What did you find?'"""
# # """벽에 걸린 수수께끼 같은 그림을 두 사람이 뚫어지게 쳐다보고, 횃불이 깜박인다.
# # 한 남자가 중얼거린다, '이게 틀림없어. 이게 바로 비밀 코드야.' 여자가 그를 보며 흥분해서 속삭인다, '뭘 찾았어?'"""

# operation = client.models.generate_videos(
#     model="veo-3.0-generate-preview",
#     prompt=prompt,
# )

# while not operation.done:
#     print("Waiting for video generation to complete...")
#     time.sleep(10)
#     operation = client.operations.get(operation)

# video = operation.response.generated_videos
# video.video.save("dialogue_example.mp4")
# print("Generated video saved to dialogue_example.mp4")
