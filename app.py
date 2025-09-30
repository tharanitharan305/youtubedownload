from flask import Flask, request, jsonify, send_from_directory
from yt_dlp import YoutubeDL
from urllib.parse import quote
import os
import logging

app = Flask(__name__)

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO)

# --- Folder to save downloads ---
# On Render, the filesystem is temporary. This is fine for this use case.
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# --- IMPORTANT: Get cookies from environment variable ---
# This is more secure and reliable than a static file.
YOUTUBE_COOKIES = os.environ.get('YOUTUBE_COOKIES_TXT')

# --- CORS Headers ---
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
    format_choice = data.get('format', 'mp4')

    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True, # Reduces console spam
    }

    # --- Use cookies if they exist in the environment ---
    if YOUTUBE_COOKIES:
        # yt-dlp needs a file path, so we create a temporary one
        temp_cookie_file = os.path.join(DOWNLOAD_FOLDER, 'cookies_temp.txt')
        with open(temp_cookie_file, 'w') as f:
            f.write(YOUTUBE_COOKIES)
        ydl_opts['cookiefile'] = temp_cookie_file
        logging.info("Using cookies for download.")
    else:
        logging.warning("No cookies found. Downloads may fail for age-restricted content.")


    if format_choice.lower() == 'mp3':
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

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if format_choice.lower() == 'mp3':
                # The filename from ydl will have .webm or similar, we need to change it to .mp3
                base, _ = os.path.splitext(filename)
                filename = base + '.mp3'


            if not os.path.exists(filename):
                 logging.error(f"File not found after download: {filename}")
                 return jsonify({'error': 'Downloaded file could not be found on the server.'}), 500

            file_url = request.host_url + 'downloads/' + quote(os.path.basename(filename))

            logging.info(f"Successfully processed and serving file: {file_url}")
            return jsonify({
                'file_url': file_url,
                'format': format_choice.lower(),
                'title': info.get('title', 'Unknown Title')
            })

    except Exception as e:
        # This provides a much more detailed error back to your Flutter app
        logging.error(f"yt-dlp error: {str(e)}")
        return jsonify({'error': f"An error occurred: {str(e)}"}), 500
    finally:
        # Clean up the temporary cookie file if it was created
        if 'cookiefile' in ydl_opts and os.path.exists(ydl_opts['cookiefile']):
            os.remove(ydl_opts['cookiefile'])


# --- Serve downloaded files ---
@app.route('/downloads/<path:filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
