# coding: utf-8
from bottle import template
from base64 import b64decode
from pathlib import Path
from furl import furl

url = lemo.api_url
stream = lemo.streams[6]
stream_id = stream["stream_id"]
print(stream)

params = lemo.params
params.update({"action": "get_simple_data_table", "stream_id": stream_id})
r = requests.get(url, params)
data = r.json()
epg_listings = data.get("epg_listings")

# -- testing -- #
channels = []
programs = []
tvg_id = stream["epg_channel_id"]
tvg_name = stream["name"]
tvg_logo = stream["stream_icon"]


epg_item = epg_listings[0]
print(epg_item)

for epg_item in epg_listings:
    epg_title = b64decode(epg_item["title"])
    epg_desc = b64decode(epg_item["description"])
    # epg_start = epg_item["start_timestamp"]
    # epg_stop = epg_item["stop_timestamp"]
    epg_start = convertEPGTime(
        pd.to_datetime(epg_item["start"], utc=True), epg_fmt=True
    )
    epg_stop = convertEPGTime(pd.to_datetime(epg_item["end"], utc=True), epg_fmt=True)

    channels.append(
        {
            "tvg_id": tvg_id,
            "tvg_name": tvg_name,
            "tvg_logo": tvg_logo,
            "epg_desc": epg_desc,
        }
    )
    programs.append(
        {
            "tvg_id": tvg_id,
            "epg_title": epg_title,
            "epg_start": epg_start,
            "epg_stop": epg_stop,
            "epg_desc": epg_desc,
        }
    )

url = furl(url).origin
tpl = str(next(Path.cwd().rglob("epg.tpl")))
print(template(tpl, channels=channels, programs=programs, url=url))
