import re
from configparser import ConfigParser
from itertools import chain
from pathlib import Path

import pandas as pd
import requests
from pandas.tseries.offsets import Week
from teddy import convertEPGTime, getEPGTimeNow


class ChapoAPI(object):
    """REST API Wrapper for ChapoStreamz!"""

    def __init__(self):
        """Configs"""
        config = ConfigParser()
        config.read(Path(Path.home(), '.config/plexarr.ini'))

        self.API_URL = config["chapo"].get('api_url')
        self.USERNAME = config["chapo"].get('username')
        self.PASSWORD = config["chapo"].get('password')
        self.PARAMS = {
            "username": self.USERNAME,
            "password": self.PASSWORD
        }
        self.CATEGORY = {}
        self.STREAMS = {}

    def getCategory(self, query=''):
        """Get Category using query filter"""
        payload = self.PARAMS
        payload.update({'action': 'get_live_categories'})
        r = requests.get(url=self.API_URL, params=payload)
        return next((cat for cat in r.json() if query.lower() in cat.get('category_name').lower()), {})

    def setCategory(self, query=''):
        """Set Category using 'query' filter"""
        payload = self.PARAMS
        payload.update({'action': 'get_live_categories'})
        r = requests.get(url=self.API_URL, params=payload)
        self.CATEGORY = next((cat for cat in r.json() if query.lower() in cat.get('category_name').lower()), {})

    def getStreams(self, terms=''):
        """Get Streams by Category_ID and filtered by 'terms'"""
        payload = self.PARAMS
        payload.update({'action': 'get_live_streams'})
        payload.update({'category_id': self.CATEGORY.get("category_id")})
        r = requests.get(url=self.API_URL, params=payload)
        return (stream for stream in r.json() if terms.lower() in stream.get('name').lower())

    def getStreamsNFL(self):
        """Get NFL Streams"""
        self.setCategory(query="NFL")
        streams = self.getStreams(terms="Gamepass")
        return streams

    def m3uNFL(self):
        """Generate m3u for NFL Streams"""
        m3u = "#EXTM3U\n"
        tvg_cuid = 801
        for i, stream in enumerate(self.getStreamsNFL()):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = stream.get("stream_icon")
            tvg_group = "NFL Gamepass"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def xmlNFL(self):
        """Generate xml for NFL Streams"""
        xml = '<?xml version="1.0" encoding="utf-8" ?>\n'
        xml += '<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
        xml += '<tv generator-info-name="IPTV" generator-info-url="http://jlwmedia.xyz:25461/">\n'
        xml_chan = ''
        xml_prog = ''
        for stream in self.getStreamsNFL():
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = stream.get("stream_icon")
            # tvg_group = "NFL Sunday Games"

            epg_desc = stream.get("name").split(":", maxsplit=1)[1].strip()
            # if epg_desc := stream.get("name").split(":", maxsplit=1)[1].strip():
            if epg_desc:
                try:
                    epg_title = epg_desc.split('(')[0].strip()
                    date_now = getEPGTimeNow(dt_obj=True).date()
                    year_now = str(date_now.year)[-2:]
                    game_time = epg_desc.split('(')[1].strip().split(')')[0].strip()

                    regex = r'(\d+).(\d+)\s+(\d+):(\d+)\s*(\w*)\s*(\w*)'
                    game_datetime = pd.to_datetime(re.sub(regex, rf'\1.\2.{year_now} \3:\4 \5', game_time))

                    epg_start = convertEPGTime(game_datetime.tz_localize('US/Eastern'), epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

                    xml_chan += f'    <channel id="{tvg_id}">\n'
                    xml_chan += f'        <display-name>{tvg_name}</display-name>\n'
                    xml_chan += f'        <icon src="{tvg_logo}"/>\n'
                    xml_chan += '    </channel>\n'

                    xml_prog += f'    <programme channel="{tvg_id}" start="{epg_start}" stop="{epg_stop}">\n'
                    xml_prog += f'        <title lang="en">{epg_title}</title>\n'
                    xml_prog += f'        <desc lang="en">{epg_desc}</desc>\n'
                    xml_prog += '    </programme>\n'
                except Exception:
                    print(stream)
                    pass
        xml = xml + xml_chan + xml_prog + '</tv>\n'
        return xml

    
