from flask import Flask, request, jsonify, send_from_directory, make_response
from yt_dlp import YoutubeDL
from urllib.parse import quote
import os
import logging
import shutil

app = Flask(__name__)

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO)

# --- Folder to save downloads ---
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# --- Path to secret cookie file (Render or local) ---
SECRET_COOKIE_FILE_PATH = '/etc/secrets/cookies.txt'

# --- Allow CORS ---
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


# --- Main Download Endpoint ---
@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing URL'}), 400

    url = data['url']
    format_choice = data.get('format', 'mp4').lower()
    temp_cookie_file_path = None

    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
    }

    # --- Copy cookie file if available ---
    if os.path.exists(SECRET_COOKIE_FILE_PATH):
        try:
            temp_cookie_file_path = os.path.join(DOWNLOAD_FOLDER, 'cookies_temp.txt')
            shutil.copyfile(SECRET_COOKIE_FILE_PATH, temp_cookie_file_path)
            ydl_opts['cookiefile'] = temp_cookie_file_path
            logging.info(f"✅ Using cookies from {SECRET_COOKIE_FILE_PATH}")
        except Exception as e:
            logging.error(f"⚠️ Failed to copy cookie file: {e}")
    else:
        logging.warning(f"⚠️ No cookie file found at {SECRET_COOKIE_FILE_PATH}")

    # --- Format handling ---
    if format_choice == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
        })

    # --- Download ---
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if format_choice == 'mp3':
                base, _ = os.path.splitext(filename)
                filename = base + '.mp3'

            if not os.path.exists(filename):
                logging.error(f"❌ File not found after download: {filename}")
                return jsonify({'error': 'Downloaded file not found on server.'}), 500

            file_url = request.host_url + 'downloads/' + quote(os.path.basename(filename))

            logging.info(f"✅ Download successful: {file_url}")

            return jsonify({
                'file_url': file_url,
                'format': format_choice,
                'title': info.get('title', 'Unknown Title')
            })

    except Exception as e:
        logging.error(f"❌ yt-dlp error: {str(e)}")
        return jsonify({'error': f"An error occurred: {str(e)}"}), 500

    finally:
        if temp_cookie_file_path and os.path.exists(temp_cookie_file_path):
            os.remove(temp_cookie_file_path)
            logging.info("🧹 Cleaned up temporary cookie file.")


# --- Serve Downloaded Files ---
@app.route('/downloads/<path:filename>', methods=['GET'])
def serve_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    response = make_response(send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True))
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "application/octet-stream"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# --- Root check ---
@app.route('/', methods=['GET'])
def root():
    return jsonify({"status": "YouTube Downloader Flask API running ✅"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
