from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/download", methods=["POST"])
def download_video():
    data = request.get_json()
    url = data.get("url")
    format_type = data.get("format", "mp4")  # default mp4

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ydl_opts = {
            'format': 'bestaudio/best' if format_type == "mp3" else 'best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        filename = ydl.prepare_filename(info)
        return jsonify({
            "title": info.get("title"),
            "file_path": filename
        })

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
