from flask import Flask, request, jsonify, send_from_directory
from yt_dlp import YoutubeDL
from urllib.parse import quote
import os

app = Flask(__name__)

# Folder to save downloads
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Cookies file for YouTube login
COOKIES_FILE = os.path.join(os.getcwd(), 'cookies.txt')  # Make sure this exists if needed

# --- CORS ---
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# --- Download endpoint ---
@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing URL'}), 400

    url = data['url']
    format_choice = data.get('format', 'mp4')  # Default to mp4, or use 'mp3'

    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'cookies': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
    }

    # MP3 options
    if format_choice.lower() == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:  # MP4 options
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if format_choice.lower() == 'mp3':
                filename = os.path.splitext(filename)[0] + '.mp3'

            # Encode URL for web-safe characters
            file_url = request.host_url + 'downloads/' + quote(os.path.basename(filename))

            return jsonify({
                'file_url': file_url,
                'format': format_choice.lower(),
                'title': info.get('title', 'Unknown Title')
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- Serve downloaded files ---
@app.route('/downloads/<path:filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
