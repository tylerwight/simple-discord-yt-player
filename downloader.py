import yt_dlp
import os
import logging


def get_song(url, max_length = 10 * 60):
    filename = 'playing.mp3'
    if os.path.exists(filename):
        os.remove(filename)

    opts_check_length = {
        'quiet': True,
        'skip_download': True,
    }
    opts_download = {
        'format': 'bestaudio/best',
        'outtmpl': 'playing.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
    }

    with yt_dlp.YoutubeDL(opts_check_length) as ydl:
        info = ydl.extract_info(url, download=False)

        duration = info.get('duration', 0)
        logging.info(f"Video duration: {duration} seconds")

        if duration > max_length:
            raise Exception(f"Video too long (max is {max_length} seconds)")
    
        with yt_dlp.YoutubeDL(opts_download) as ydl2:
            ydl2.download([url])

        
        return filename
        

def get_title(url):
    logging.info("Getting Title")
    opts = {
        "quiet": True,
        "skip_download": True
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get("title", None)

    return title