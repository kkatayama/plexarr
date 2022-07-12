#!/usr/local/bin/genv python3
import grequests
from plexarr import LemoAPI
from bottle import template
from pathlib import Path

from itertools import chain
from teddy import convertEPGTime, convert_bytes
from base64 import b64decode
from furl import furl
import pandas as pd
import argparse
import requests
import time


def channel(s):
    return {
        "s_id": s["stream_id"],
        "tvg_id": s["epg_channel_id"],
        "tvg_name": s["name"],
        "tvg_logo": s["stream_icon"],
    }

def program(r):
    global INIT
    global cmd

    if INIT:
        print(r.json().get('epg_listings')[0])
        INIT = False
    key = "end" if cmd == "get_simple_data_table" else "stop"

    return (
        {
            "tvg_id": i["channel_id"],
            "epg_title": b64decode(i["title"]).decode(errors="ignore"),
            "epg_start": convertEPGTime(pd.to_datetime(i["start"], utc=True), epg_fmt=True),
            "epg_stop": convertEPGTime(pd.to_datetime(i[key], utc=True), epg_fmt=True),
            "epg_desc": b64decode(i["description"]).decode(errors="ignore"),
        }
        for i in r.json().get("epg_listings")
    )



if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--cmd", required=False, default="get_short_epg", help="xtream codes action {get_short_epg, get_simple_data_table}")
    ap.add_argument("-b", "--batch_size", default=5, required=False, help="#urls to download simultaneously")
    args = ap.parse_args()

    # -- CONFIGS -- #
    cmd = str(args.cmd)
    batch_size = int(args.batch_size)
    INIT = True

    # -- START -- #
    lemo = LemoAPI()
    lemo_m3u = lemo.getM3U()
    url = lemo.api_url
    print(f'#streams: {len(lemo.streams)}')

    channels = [channel(s) for s in lemo.streams if s["epg_channel_id"]]
    print(f'#channels: {len(channels)}')

    params = lemo.params
    # params.update({"action": "get_simple_data_table"})
    params.update({"action": cmd})
    payloads = [dict(**params, **{"stream_id": c["s_id"]}) for c in channels]
    programs = []

    print(f'\nstarting downloads...\nbatch_size: {batch_size}\ncmd: {cmd}')
    start = time.time()
    while payloads:
        batch = payloads[:batch_size]
        # gs = (grequests.get(url, params=payload, stream=False) for payload in payloads)
        gs = (grequests.get(url, params=payload, stream=False) for payload in batch)
        # programs = list(chain(*(program(r) for r in grequests.map(gs))))
        batch_programs = list(chain(*(program(r) for r in grequests.map(gs))))
        programs += batch_programs
        payloads = payloads[batch_size:]
    end = time.time()
    total = end - start
    print(f'downloads finished!\ntook: {total:.2f} seconds\n')
    print(f'#programs: {len(programs)}')

    url = furl(url).origin
    tpl = str(next(Path.cwd().rglob("epg.tpl")))
    epg = template(tpl, channels=channels, programs=programs, url=url)
    print(f'epg.xml size: {convert_bytes(len(epg))}')
