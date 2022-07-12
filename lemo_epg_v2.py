# coding: utf-8
from plexarr import LemoAPI
from bottle import template
from pathlib import Path

from itertools import chain
from teddy import convertEPGTime
from base64 import b64decode
from furl import furl
import pandas as pd
import requests


lemo = LemoAPI()
lemo_m3u = lemo.getM3U()

url = lemo.api_url
stream = lemo.streams[6]
stream_id = stream["stream_id"]
print(stream)


def channel(s):
    return {
        "s_id": s["stream_id"],
        "tvg_id": s["epg_channel_id"],
        "tvg_name": s["name"],
        "tvg_logo": s["stream_icon"],
    }


channels = [channel(s) for s in lemo.streams]


def program(c):
    def epg_item(i):
        return {
            "tvg_id": c["tvg_id"],
            "epg_title": b64decode(i["title"]).decode(errors="ignore"),
            "epg_start": convertEPGTime(
                pd.to_datetime(i["start"], utc=True), epg_fmt=True
            ),
            "epg_stop": convertEPGTime(
                pd.to_datetime(i["end"], utc=True), epg_fmt=True
            ),
            "epg_desc": b64decode(i["description"]).decode(errors="ignore"),
        }

    params = lemo.params
    params.update({"action": "get_simple_data_table", "stream_id": c["s_id"]})
    r = requests.get(url, params)
    data = r.json()
    return (epg_item(i) for i in data.get("epg_listings"))


programs = list(chain(*(program(c) for c in channels[:4])))


url = furl(url).origin
tpl = str(next(Path.cwd().rglob("epg.tpl")))
print(template(tpl, channels=channels, programs=programs, url=url))
