import os
from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'URL required'}), 400

    ydl_opts = {}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        result = {
            'title': info.get('title'),
            'id': info.get('id'),
            'duration': info.get('duration'),
            'thumbnail': info.get('thumbnail'),
            'formats': info.get('formats')  # or filter best
        }
    return jsonify({'status': 'success', 'data': result})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
