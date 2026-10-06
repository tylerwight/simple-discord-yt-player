import yt_dlp
import os
import logging
import asyncio

cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
logger = logging.getLogger(__name__)

def get_song(url, max_length = 10 * 60):
    logging.info("inside get_song")
    filename = 'playing.mp3'
    if os.path.exists(filename):
        os.remove(filename)
    
    opts_check_length = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
        "playlist_items": "1",
        'cookiefile': cookies_path,
    }
    opts_download = {
        'format': 'bestaudio/best',
        'outtmpl': 'playing.%(ext)s',
        'noplaylist': True,
        "playlist_items": "1",
        'cookiefile': cookies_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
    }

    with yt_dlp.YoutubeDL(opts_check_length) as ydl:
        logging.info("Checking Video length before download")
        info = ydl.extract_info(url, download=False)

        duration = info.get('duration', 0)
        logging.info(f"Video duration: {duration} seconds")

        if duration > max_length:
            raise Exception(f"Video too long (max is {max_length} seconds)")
    
        with yt_dlp.YoutubeDL(opts_download) as ydl2:
            logging.info("Downloading video")
            ydl2.download([url])

        
        return filename
        

def get_title_blocking(url):
    logging.info("Getting Title")
    opts = {
        "quiet": True,
        "skip_download": True,
        'noplaylist': True,
        "playlist_items": "1",
        'cookiefile': cookies_path,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get("title", None)

    return title

async def get_title(url):
    return await asyncio.to_thread(get_title_blocking, url)




def get_playlist_entries_blocking(url: str):
    # returns a list of dicts that include the title and URLs for a given youtube URL containing a playlist

    opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,  
        "noplaylist": False,
        'cookiefile': cookies_path,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries") or []
    results = []

    logger.info(f"got this info from url: {info}\n\n\n ENTRIES: {entries} len: {len(entries)}  \n\n URL: {info.get('url')}")

    #if this was a mix URL, extract the playlist URL and re-run
    if (len(entries) == 0) and ("youtube.com/playlist" in info.get("url")):
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(info.get("url"), download=False)
        entries = info.get("entries") or []


    for entry in entries:
        if not entry:
            continue
    
        title = entry.get("title") or "Unknown Title"
        logger.info(f"found title: {title}")
        vid_id = entry.get("id")
        webpage_url = entry.get("webpage_url") or entry.get("url")
        logger.info(f"found web_url & url: {webpage_url}")
        if webpage_url and webpage_url.startswith("http"):
            video_url = webpage_url
        elif vid_id:
            video_url = f"https://www.youtube.com/watch?v={vid_id}"
        else:
            continue

        results.append({"title": title, "url": video_url})
    
    
    return results

async def get_playlist_entries(url: str):
    return await asyncio.to_thread(get_playlist_entries_blocking, url)



def search_youtube_top_result_blocking(query: str) -> dict | None:
    opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": True, 
        'cookiefile': cookies_path,
    }

    search_term = f"ytsearch1:{query}"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(search_term, download=False)

    entries = info.get("entries") or []
    if not entries:
        return None

    top = entries[0] or {}
    title = top.get("title") or "Unknown Title"
    url = top.get("webpage_url") or top.get("url")
    vid_id = top.get("id")

    if url and isinstance(url, str) and url.startswith("http"):
        video_url = url
    elif vid_id:
        video_url = f"https://www.youtube.com/watch?v={vid_id}"
    else:
        return None

    return {"title": title, "url": video_url}


async def search_youtube_top_result(query: str) -> dict | None:
    return await asyncio.to_thread(search_youtube_top_result_blocking, query)