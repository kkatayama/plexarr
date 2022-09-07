import re
from configparser import ConfigParser
# from itertools import chain
from pathlib import Path

import pandas as pd
import requests
# from pandas.tseries.offsets import Week
from rich import inspect
from teddy import convertEPGTime, getEPGTimeNow
from bottle import template
from furl import furl
# from .utils import gen_xmltv_xml


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

    def getCategories(self, groups='', terms=''):
        """
        Get All Categories in Matching Groups

        ARGS:
            groups (str|list) - ex: "USA Sports" or ['USA News', 'USA Sports']
        """
        payload = self.PARAMS
        payload.update({'action': 'get_live_categories'})
        r = requests.get(url=self.API_URL, params=payload)

        if groups:
            return list(filter(lambda x: x["category_name"] in groups, r.json()))
        if terms:
            terms = [terms] if isinstance(terms, str) else terms
            return list(filter(lambda x: any(term in x["category_name"].lower() for term in terms), r.json()))
        return r.json()


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

    def getStreams(self, terms='', bad_terms='BAD TERMS'):
        """Get Streams by Category_ID and filtered by 'terms'"""
        payload = self.PARAMS
        payload.update({'action': 'get_live_streams'})
        payload.update({'category_id': self.CATEGORY.get("category_id")})
        r = requests.get(url=self.API_URL, params=payload)
        return (stream for stream in r.json() if terms.lower() in stream.get('name').lower() and bad_terms not in stream.get('name'))

    def getStreamsNFL(self, terms=[], rejects=[]):
        """Get NFL Streams"""
        terms = [terms.lower()] if isinstance(terms, str) else [t.lower() for t in terms]
        rejects = [rejects.lower()] if isinstance(rejects, str) else [r.lower() for r in rejects]

        self.setCategory(query="NFL")
        # streams = self.getStreams(terms="Gamepass")
        # streams = self.getStreams(terms="PM")
        streams = self.getStreams()
        return list(filter(lambda x: any(t in x["name"].lower() and all(r not in x["name"].lower() for r in rejects) for t in terms), streams))

    def getStreamsNBA(self):
        """Get NBA Streams"""
        self.setCategory(query="NBA")
        streams = self.getStreams(terms="NBA ", bad_terms="*")
        return streams

    def m3uNFL(self):
        """Generate m3u for NFL Streams"""
        m3u = "#EXTM3U\n"
        tvg_cuid = 702
        for i, stream in enumerate(self.getStreamsNFL(terms=['nfl 0', 'nfl 1'])):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = stream.get("stream_icon")
            tvg_group = "NFL Gamepass"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uNBA(self):
        """Generate m3u for NBA Streams"""
        m3u = "#EXTM3U\n"
        tvg_cuid = 801
        for i, stream in enumerate(self.getStreamsNBA()):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = stream.get("stream_icon")
            tvg_group = "NBA Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def xmlNFL(self):
        """Generate xml for NFL Streams"""
        channels = []
        programs = []
        for stream in self.getStreamsNFL():
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = stream.get("stream_icon")
            # tvg_group = "NFL Sunday Games"

            epg_desc = stream.get("name").split(":", maxsplit=1)[1].strip()
            ##### THIS IS TEMPORARY FOR SUPER BOWL FIX ####
            # epg_desc = epg_desc.replace("02.11", "02.13")

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

                    if ((date_now - game_datetime.date()).days < 5):
                        channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                        programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})

                except Exception as e:
                    try:
                        epg_title = epg_desc.split('(')[0].strip()
                        date_now = getEPGTimeNow(dt_obj=True).date()
                        year_now = str(date_now.year)[-2:]
                        game_time = epg_desc.split("PM")[0].strip() + ":00 PM"

                        game_datetime = pd.to_datetime(game_time)
                        epg_start = convertEPGTime(game_datetime.tz_localize('US/Eastern'), epg_fmt=True)
                        epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
                        if ((date_now - game_datetime.date()).days < 5):
                            channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                            programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})
                    except Exception as e:
                        inspect(e)
                        pass
        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)

    def xmlNBA(self):
        """Generate xml for NBA Streams"""
        channels = []
        programs = []
        for stream in self.getStreamsNBA():
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

                    if ((date_now - game_datetime.date()).days < 5):
                        channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                        programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})

                except Exception as e:
                    inspect(e)
                    pass
        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)
