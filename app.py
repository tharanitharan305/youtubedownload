from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Ensure downloads folder exists
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)


@app.route("/download", methods=["POST"])
def download_youtube():
    """
    Expects JSON: { "url": "<youtube_link>", "format": "mp4" or "mp3" }
    Returns JSON with file path and title.
    """
    data = request.json
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' in request"}), 400

    url = data["url"]
    fmt = data.get("format", "mp4").lower()
    if fmt not in ["mp4", "mp3"]:
        return jsonify({"error": "Invalid format, must be 'mp4' or 'mp3'"}), 400

    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s"),
    }

    if fmt == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        ydl_opts.update({
            "format": "bestvideo+bestaudio/best",
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            if fmt == "mp3":
                file_path = os.path.splitext(file_path)[0] + ".mp3"

        file_url = request.host_url + "downloads/" + os.path.basename(file_path)
        return jsonify({
            "file_url": file_url,
            "format": fmt,
            "title": info.get("title")
        })

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/downloads/<filename>")
def serve_file(filename):
    """Serve downloaded files"""
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
