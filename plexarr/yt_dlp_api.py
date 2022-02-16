import os
from configparser import ConfigParser

import yt_dlp
import yt_dlp.utils
from rich import print
from rich.progress import Progress


class MyLogger(object):
    def info(self, msg):
        print(msg)
        pass

    def debug(self, msg):
        # if msg.startswith('[debug] '):
        #     pass
        # else:
        #     self.info(msg)
        # pass
        pass

    def warning(self, msg):
        # print(msg)
        pass

    def error(self, msg):
        # print(msg)
        pass


class YouTubeDLP(object):
    """Wrapper for YouTubeDLP via yt_dlp
    """
    def __init__(self):
        """Constructor

        From config:
            cookies (str): Path to Cookies File
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

        self.path = config['youtube'].get('path')
        self.temp_dir = config['youtube'].get('temp_dir')
        self.cookies = config['youtube'].get('cookies')
        self.progress = Progress()
        self.task = None
        self.downloaded_bytes = 0
        self.download_status = False

    # -- https://stackoverflow.com/a/58667850/3370913
    def my_hook(self, d):
        # print(d)
        if d['status'] == 'finished':
            self.progress.stop()
            file_tuple = os.path.split(os.path.abspath(d['filename']))
            print(f'Done downloading "{file_tuple[1]}"')
        if d['status'] == 'downloading':
            if not self.download_status:
                try:
                    total = int(d["total_bytes"])
                except Exception:
                    total = int(d["total_bytes_estimate"])
                self.download_status = True
                self.task = self.progress.add_task("[cyan]Downloading...", total=total)
                self.progress.start()
            step = int(d["downloaded_bytes"]) - int(self.downloaded_bytes)
            self.downloaded_bytes = int(d["downloaded_bytes"])
            self.progress.update(self.task, advance=step)
            # print(d['filename'], d['_percent_str'], d['_eta_str'])

    def getInfo(self, media, video, audio):
        vsize = video["stream_size"]
        asize = audio["stream_size"]
        width = video["width"]
        height = video["height"]
        vcodec = video["codec_id"].split("-")[0]
        acodec = audio["codec_id"].split("-")[0]

        fps = round(float(video["frame_rate"]))
        ext = media["file_extension"]
        asr = audio["sampling_rate"]
        query = media["file_name"]

        video_format = f'bestvideo[height={height}][width={width}][ext={ext}][fps={fps}][vcodec*={vcodec}][filesize>={vsize}]'
        audio_format = f'bestaudio[acodec*={acodec}][asr={asr}][filesize>={asize}]'

        ytdl_opts = {
            'noplaylist': True,
            'ignoreerrors': True,
            'cookiefile': self.cookies,
            'default_search': 'ytsearch10',
            'format': f'{video_format}+{audio_format}',
            'logger': MyLogger(),
            'progress_hooks': [self.my_hook]
        }

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            msize = media["file_size"]
            results = ytdl.extract_info(query, download=False)
            matches = [r for r in results["entries"] if ((r is not None) and (abs(msize-r["filesize_approx"]) < 1000000))]
            print(f'results: {len(results["entries"])}, matches: {len(matches)}')
            return matches

