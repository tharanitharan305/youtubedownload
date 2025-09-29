# app.py
from flask import Flask, request, jsonify, send_file, after_this_request
import tempfile
import os
import shutil
import logging
from yt_dlp import YoutubeDL

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/download", methods=["POST"])
def download():
    """
    POST JSON: { "url": "<youtube url>", "format": "mp3" | "mp4" }
    Response: streamed file as attachment (Content-Disposition)
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    url = data.get("url")
    fmt = (data.get("format") or "mp3").lower()

    if not url or fmt not in ("mp3", "mp4"):
        return jsonify({"error": "Provide 'url' and 'format' (mp3 or mp4)"}), 400

    tmpdir = tempfile.mkdtemp(prefix="yd_")
    outtmpl = os.path.join(tmpdir, "%(id)s.%(ext)s")

    # Build yt-dlp options
    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
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
    else:  # mp4
        ydl_opts.update({
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        })

    try:
        app.logger.info("Starting download: url=%s format=%s", url, fmt)
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info or "id" not in info:
            raise RuntimeError("Failed to extract info")

        # Expected output filename
        if fmt == "mp3":
            expected = f"{info['id']}.mp3"
        else:
            expected = f"{info['id']}.mp4"

        file_path = os.path.join(tmpdir, expected)
        # Fallback: find any file in tmpdir
        if not os.path.exists(file_path):
            files = os.listdir(tmpdir)
            if files:
                # pick the first large file
                files.sort(key=lambda fn: os.path.getsize(os.path.join(tmpdir, fn)), reverse=True)
                file_path = os.path.join(tmpdir, files[0])
            else:
                raise RuntimeError("No output file was generated")

        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            raise RuntimeError("Output file missing or empty: " + file_path)

        @after_this_request
        def cleanup(response):
            try:
                shutil.rmtree(tmpdir)
                app.logger.info("Cleaned up tmpdir %s", tmpdir)
            except Exception as e:
                app.logger.error("Cleanup failed: %s", e)
            return response

        # Determine mimetype - let Flask guess if uncertain
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        app.logger.exception("Download error")
        # best-effort cleanup
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # For local tests only. Render will use gunicorn via Dockerfile.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
