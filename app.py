import os
from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

# Create downloads folder if it doesn't exist
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return "YouTube Downloader API is running!"

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "Please provide a YouTube URL"}), 400

    url = data["url"]
    format_type = data.get("format", "mp4").lower()  # default mp4

    # yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == "mp3" else 'best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }

    # Add postprocessor if mp3 is requested
    if format_type == "mp3":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)
            if format_type == "mp3":
                # Replace extension with mp3 after conversion
                file_path = os.path.splitext(file_path)[0] + ".mp3"

        return jsonify({
            "file_path": file_path,
            "title": info_dict.get("title", "Unknown Title"),
            "format": format_type
        })

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # For Render, use 0.0.0.0 and port from env
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
