from flask import Flask, request, jsonify, send_from_directory
import os
import yt_dlp

app = Flask(__name__)

# Folder to store downloaded files
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/download", methods=["POST"])
def download_youtube():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data["url"]
    format_choice = data.get("format", "mp4")  # default is mp4

    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s"),
        "format": "bestaudio/best" if format_choice == "mp3" else "best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ] if format_choice == "mp3" else [],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "file")
            ext = "mp3" if format_choice == "mp3" else info.get("ext", "mp4")
            filename = f"{title}.{ext}"
            file_url = request.host_url + "downloads/" + filename
            return jsonify({
                "file_url": file_url,
                "format": ext,
                "title": title
            })

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": str(e)}), 500

# Serve downloaded files
@app.route("/downloads/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
