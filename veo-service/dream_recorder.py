from flask import Flask, request, jsonify
from flask_cors import CORS
import time, datetime, os
from google import genai
from google.genai.types import GenerateVideosConfig
from google.cloud import storage
from urllib.parse import urlparse

from dotenv import load_dotenv 
load_dotenv()

app = Flask(__name__)
CORS(app)  # 추가 — React에서 요청 가능하게

storage_client = storage.Client()

def generate_signed_url(gcs_uri: str, expiration_minutes: int = 15):
    parsed = urlparse(gcs_uri)
    bucket_name = parsed.netloc
    object_name = parsed.path.lstrip('/')

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expiration_minutes),
        method="GET",
    )
    return url

@app.route("/generate-video", methods=["POST"])
def generate_video():
    data = request.get_json()
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    
    # ⬇️⬇️⬇️ 디버깅을 위해 이 줄을 추가하세요 ⬇️⬇️⬇️
    print(f"======= AI에게 전달될 프롬프트: {prompt} =======")

    output_gcs_uri = os.getenv("OUTPUT_GCS_URI")
    if not output_gcs_uri or not output_gcs_uri.startswith("gs://"):
        return jsonify({"error": "invalid OUTPUT_GCS_URI"}), 500

    try:
        client = genai.Client()
        operation = client.models.generate_videos(
            model="veo-3.0-generate-001",
            prompt=prompt,
            config=GenerateVideosConfig(
                aspect_ratio="16:9",
                output_gcs_uri=output_gcs_uri,
                duration_seconds=8
            ),
        )

        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        if operation.error:
            msg = getattr(operation.error, "message", str(operation.error))
            return jsonify({"error": msg}), 500

        gcs_uri = operation.result.generated_videos[0].video.uri
        signed_url = generate_signed_url(gcs_uri)

        return jsonify({
            "message": "비디오 생성 완료",
            "signed_url": signed_url
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
