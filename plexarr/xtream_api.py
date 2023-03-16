import grequests
from configparser import ConfigParser
from ast import literal_eval
from pathlib import Path
from itertools import chain
# from teddy import getLogger
from .utils import getLogger
import requests
import re
import os


log = getLogger()

class XtreamAPI:
    """MultiThreaded API For LemoIPTV and ChapoIPTV"""

    def __init__(self):
        """Configs"""
        config = ConfigParser()
        config.read(Path(Path.home(), ".config/plexarr.ini"))
        self.config = config

    def setup(self, iptv):
        config = self.config
        key = re.sub(r'\d+', '', iptv)
        groups = f'{key}_groups'
        info = {
            "api_url": config[iptv].get("api_url"),
            "username": config[iptv].get("username"),
            "password": config[iptv].get("password"),
            "groups": literal_eval(config[iptv].get(groups)),
            "params": {
                "username": config[iptv].get("username"),
                "password": config[iptv].get("password")
            },
            "category": {},
            "streams": [],
        }
        #exec(f'self.{iptv} = info')
        self.__dict__[iptv] = info

    def genInfo(self, s):
        tvg_id = s["epg_channel_id"] if s.get("epg_channel_id") else ""
        tvg_name = s["name"] if s.get("name") else ""
        tvg_logo = s["stream_icon"] if s.get("stream_icon") else ""
        tvg_group = next((c["category_name"] for c in self.cats if s["category_id"] == c["category_id"]), "")
        return f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'

    def genM3U(self, s, iptv):
        api_url = eval(f'self.{iptv}["api_url"]')
        username = eval(f'self.{iptv}["username"]')
        password = eval(f'self.{iptv}["password"]')

        return api_url.replace(
            "/player_api.php",
            f':80/{username}/{password}/{s.get("stream_id")}.ts\n',
        )

    def process(self, r, iptv, **kwargs):
        streams = r.json()
        self.streams += streams
        m3u_streams = []
        for s in streams:
            m3u_streams += [self.genInfo(s)] + [self.genM3U(s, iptv)]
        return m3u_streams

    def getCategories(self, iptv):
        """Get All Categories in Matching Groups"""
        api_url = eval(f'self.{iptv}["api_url"]')
        payload = eval(f'self.{iptv}["params"]')
        groups = eval(f'self.{iptv}["groups"]')
        payload.update({"action": "get_live_categories"})

        r = requests.get(url=api_url, params=payload)
        return list(filter(lambda x: x["category_name"] in groups, r.json()))

    def parseCategories(self, extract_categories, iptv):
        self.m3u_items = ["#EXTM3U\n"]
        api_url = eval(f'self.{iptv}["api_url"]')
        p = eval(f'self.{iptv}["params"]')
        p.update({"action": "get_live_streams"})
        categories = [dict(**p, **{"category_id": c["category_id"]}) for c in self.cats]

        batch_size = 8
        payloads = [categories[i:i+batch_size] for i in range(0, len(categories), batch_size)]
        for batch in payloads:
            gs = (grequests.get(api_url, params=payload, stream=False) for payload in batch)
            self.m3u_items += list(chain(*(self.process(r, iptv) for r in grequests.map(gs))))

        self.m3u = "".join(self.m3u_items)
        self.categories = categories if extract_categories else None
        return self.m3u

    def getM3U(self, extract_categories=False, iptv=''):
        self.setup(iptv)
        self.streams = []
        self.cats = self.getCategories(iptv)
        return self.parseCategories(extract_categories, iptv)




# -- TESTING -- #
# lemo = XtreamAPI()
# lemo_m3u = lemo.getM3U(extract_categories=True, iptv='lemo')

# print("\n".join(lemo_m3u.splitlines()[:20]))
# print("".join(lemo.m3u_items[:10]))
