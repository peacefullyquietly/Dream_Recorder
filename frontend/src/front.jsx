import { useState } from "react";

export default function DreamRecorder() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [videoUrl, setVideoUrl] = useState("");
  const [error, setError] = useState(null); // 오류 메시지 상태

  const generateVideo = async () => {
    setLoading(true);
    setVideoUrl("");
    setError(null); // 오류 상태 초기화

    try {
      const res = await fetch("http://localhost:8080/generate-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      const data = await res.json();

      if (res.ok && data.signed_url) {
        setVideoUrl(data.signed_url);
      } else {
        // 서버에서 받은 오류 메시지를 상태에 저장
        setError(data.error || "알 수 없는 오류가 발생했습니다.");
      }
    } catch (err) {
      // 네트워크 오류 등 fetch 실패 시
      setError("서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.");
    } finally {
      setLoading(false);
    }
  };

  return (

    <div className="flex min-h-screen w-full flex-col items-center justify-center bg-gray-900 p-4 text-white">
      <div className="w-full max-w-md rounded-2xl bg-gray-800 p-8 shadow-2xl">
        <div className="flex w-full flex-col items-center gap-6">
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">
            🌙 Dream Recorder
          </h1>

          <textarea
            placeholder="당신의 꿈 속 한 장면을 선명하게 적어주세요..."
            className="h-36 w-full rounded-xl border border-gray-700 bg-gray-900 p-4 text-gray-100 placeholder-gray-500 transition-all duration-300 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />

          <button
            className="w-full rounded-xl bg-indigo-600 px-6 py-3 text-lg font-semibold text-white shadow-lg transition-all duration-300 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={generateVideo}
            disabled={loading || !prompt} // 프롬프트가 없어도 비활성화
          >
            {loading ? "꿈을 기록 중..." : "꿈 기록 불러오기"}
          </button>
        </div>
      </div>

      {videoUrl && (
        <div className="mt-8 flex w-full max-w-sm flex-col items-center gap-4">
          <video
            src={videoUrl}
            controls
            autoPlay // 영상이 로드되면 바로 재생
            className="w-full rounded-2xl shadow-2xl"
          />
          <a
            href={videoUrl}
            download="dream_video.mp4"
            className="text-indigo-300 transition-colors hover:text-indigo-200"
          >
            🎬 영상 다운로드
          </a>
        </div>
      )}

      {loading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-4 rounded-2xl bg-gray-800 p-8 shadow-2xl">
            {/* Tailwind로 만든 스피너 */}
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-solid border-indigo-400 border-t-transparent"></div>
            <span className="text-lg font-medium text-white">
              💤 꿈을 기록 중입니다...
            </span>
            <span className="text-sm text-gray-400">
              잠시만 기다려주세요.
            </span>
          </div>
        </div>
      )}

      {/* 7. 오류 발생 시 보여줄 모달 (alert 대체) */}
      {error && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 backdrop-blur-sm"
          onClick={() => setError(null)} // 바깥 클릭 시 닫힘
        >
          <div 
            className="flex w-full max-w-sm flex-col items-center gap-4 rounded-2xl bg-gray-800 p-8 text-center shadow-2xl"
            onClick={(e) => e.stopPropagation()} // 모달 안쪽 클릭은 닫히지 않게
          >
            <span className="text-3xl">😕</span>
            <h3 className="text-lg font-semibold text-red-400">오류 발생</h3>
            <p className="text-sm text-gray-300">{error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-4 w-full rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition-transform hover:scale-105"
            >
              확인
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
