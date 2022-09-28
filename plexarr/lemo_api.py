import grequests
from configparser import ConfigParser
from ast import literal_eval
from pathlib import Path
from itertools import chain
# from teddy import getLogger
from .utils import getLogger
import requests
import os


log = getLogger()
HTTPBIN_URL = os.environ.get('HTTPBIN_URL', 'http://httpbin.org/')

def httpbin(*suffix):
    """Returns url for HTTPBIN resource."""
    return HTTPBIN_URL + '/'.join(suffix)


class LemoAPI:
    """MultiThreaded API For LemoIPTV"""

    def __init__(self):
        """Configs"""
        config = ConfigParser()
        config.read(Path(Path.home(), ".config/plexarr.ini"))

        self.api_url = config["lemo"].get("api_url")
        self.username = config["lemo"].get("username")
        self.password = config["lemo"].get("password")
        self.groups = literal_eval(config["lemo"].get("lemo_groups"))
        self.params = {"username": self.username, "password": self.password}
        self.category = {}
        self.streams = []

    def genInfo(self, s):
        tvg_id = s["epg_channel_id"] if s.get("epg_channel_id") else ""
        tvg_name = s["name"] if s.get("name") else ""
        tvg_logo = s["stream_icon"] if s.get("stream_icon") else ""
        tvg_group = next((c["category_name"] for c in self.cats if s["category_id"] == c["category_id"]), "")
        return f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'

    def genM3u(self, s):
        return self.api_url.replace(
            "/player_api.php",
            f':80/{self.username}/{self.password}/{s.get("stream_id")}.ts\n',
        )

    def process(self, r, **kwargs):
        streams = r.json()
        self.streams += streams
        m3u_streams = []
        for s in streams:
            m3u_streams += [self.genInfo(s)] + [self.genM3u(s)]
        return m3u_streams

    def getCategories(self):
        """Get All Categories in Matching Groups"""
        payload = self.params
        payload.update({"action": "get_live_categories"})
        r = requests.get(url=self.api_url, params=payload)
        return list(filter(lambda x: x["category_name"] in self.groups, r.json()))

    def parseCategories(self, extract_categories=False):
        self.m3u_items = ["#EXTM3U\n"]
        p = self.params
        p.update({"action": "get_live_streams"})
        categories = [dict(**p, **{"category_id": c["category_id"]}) for c in self.cats]

        batch_size = 8
        payloads = [categories[i:i+batch_size] for i in range(0, len(categories), batch_size)]
        for batch in payloads:
            gs = (grequests.get(self.api_url, params=payload, stream=False) for payload in batch)
            self.m3u_items += list(chain(*(self.process(r) for r in grequests.map(gs))))

        # payloads = categories[:]
        # while payloads:
        #     batch = payloads[:batch_size]
        #     gs = (grequests.get(self.api_url, params=payload, stream=False) for payload in batch)
        #     self.m3u_items += list(chain(*(self.process(r) for r in grequests.map(gs))))
        #     payloads = payloads[batch_size:]

        """
        try:
            # gs = [(grequests.get(httpbin('delay/1'), timeout=0.001), grequests.get(self.api_url, params=c) for c in categories)]
            gs = (grequests.get(self.api_url, params=c) for c in categories)
            self.m3u_items += list(chain(*(self.process(r) for r in grequests.map(gs))))
        except Exception as e:
            log.error(e.__dict__)
            gs = (requests.get(self.api_url, params=c) for c in categories)
            self.m3u_items += list(chain(*(self.process(r) for r in gs)))
        """
        self.m3u = "".join(self.m3u_items)
        self.categories = categories if extract_categories else None
        return self.m3u

    def getM3U(self, extract_categories=False):
        self.streams = []
        self.cats = self.getCategories()
        return self.parseCategories(extract_categories)

    def validateM3U(self, m3u_file="/Users/katayama/Documents/MangoBoat/IP_TV_Stuff/KEMO_iPTV/lemo.m3u"):
        with open(m3u_file) as f:
            m3u_raw = f.read()
        for line in self.m3u.splitlines():
            if line not in m3u_raw:
                print(line)



# -- TESTING -- #
# lemo = LemoAPI(groups=lemo_groups)
# lemo_m3u = lemo.getM3U(extract_streams=True, extract_categories=True)
# lemo.validateM3U()

# print("\n".join(lemo_m3u.splitlines()[:20]))
# print("".join(lemo.m3u_items[:10]))
