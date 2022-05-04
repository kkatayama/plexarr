from teddy import getEPGTimeNow, convertEPGTime
from .chapo_api import ChapoAPI
from pathlib import Path
from bottle import template
from furl import furl
import pandas as pd
import requests


class PlutoAPI(ChapoAPI):
    """REST API Wrapper for PlutoTV"""
    def __init__(self):
        """Init"""
        self.api_pluto_url = "http://api.pluto.tv/v2/channels"
        self.today = getEPGTimeNow(dt_obj=True)
        self.start = self.today.strftime("%Y-%m-%d %H:%M:%S.000%z")
        self.stop = (self.today + pd.DateOffset(days=2)).strftime("%Y-%m-%d %H:%M:%S.000%z")
        self.channels = {}
        self.episodes = {}
        super().__init__()

    def setChannels(self, start="", stop=""):
        """Save All Pluto Channels"""
        if not start:
            start = self.start
        if not stop:
            stop = self.stop
        params = {
            "start": start,
            "stop": stop,
        }
        r = requests.get(self.api_pluto_url, params=params)
        channels = r.json()
        self.channels = channels

    def getChannels(self):
        """Get All Pluto Channels"""
        if not self.channels:
            self.setChannels()
        return self.channels

    def getChannel(self, term=""):
        """Filter Single Channel"""
        channels = self.getChannels()

        data = next(filter(lambda x: term.lower() in x["name"].lower(), channels))
        info = {k: v for k, v in data.items() if k in data.keys() and k != "timelines"}
        episodes = data["timelines"]
        self.channel_data = data
        self.channel_info = info
        self.channel_episodes = episodes
        return info, episodes

    def m3uScience(self):
        """Generate m3u For Pluto Science"""
        channel_info, episodes = self.getChannel(term="science")
        stream = next(self.getStreams(terms="Pluto: Science", bad_terms="2"))

        tvg_cuid = 280
        tvg_id = stream.get("stream_id")
        tvg_name = stream.get("name")
        tvg_logo = self.channel_info["featuredImage"]["path"]
        tvg_group = "Pluto TV"

        m3u = "#EXTM3U\n"
        m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
        m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
        return m3u

    def xmlScience(self):
        """Generate EPG XML for Pluto Science"""
        channel_info, episodes = self.getChannel(term="science")

        channels = []
        tvg_id = "SCIENCE"
        tvg_name = "Pluto: Science"
        tvg_logo = self.channel_info["featuredImage"]["path"]
        channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo})

        programs = []
        for episode in episodes:
            epg_desc = episode["episode"]["description"]
            epg_title = episode["title"]
            epg_start = convertEPGTime(episode["start"], epg_fmt=True)
            epg_stop = convertEPGTime(episode["stop"], epg_fmt=True)
            epg_icon = episode["episode"]["poster"]["path"]
            programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop,
                             "epg_desc": epg_desc, "epg_icon": epg_icon})

        url = furl(self.api_plut_url).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)
            
# pluto = PlutoAPI()
# pluto.xmlScience()
