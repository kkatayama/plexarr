# coding: utf-8
from teddy import getEPGTimeNow, convertEPGTime
from bottle import template
from furl import furl
import pandas as pd
import requests
import pkg_resources


tpl = pkg_resources.resource_filename('templates', 'epg.tpl')

class PlutoAPI(object):
    """REST API Wrapper for PlutoTV"""
    def __init__(self):
        """Init"""
        self.api_url = "http://api.pluto.tv/v2/channels"
        self.today = getEPGTimeNow(dt_obj=True)
        self.start = self.today.strftime("%Y-%m-%d %H:%M:%S.000%z")
        self.stop = (self.today + pd.DateOffset(days=2)).strftime("%Y-%m-%d %H:%M:%S.000%z")
        self.channels = {}
        self.episodes = {}

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
        r = requests.get(self.api_url, params=params)
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

    def xmlScience(self):
        """Generate EPG XML for Pluto Science"""
        channel_info, episodes = self.getChannel(term="science")

        channels = []
        tvg_id = "SCIENCE"
        tvg_name = "Pluto: Science"
        tvg_logo = self.channel_info["featuredImage"]
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

        url = furl(self.api_url).origin
        return template(tpl, channels=channels, programs=programs, url=url)
            
# pluto = PlutoAPI()
# pluto.xmlScience()
