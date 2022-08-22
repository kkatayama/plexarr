from configparser import ConfigParser
from itertools import chain
from pathlib import Path

import pandas as pd
import requests
from pandas.tseries.offsets import Week
from teddy import convertEPGTime, getEPGTimeNow
from bottle import template
from furl import furl
# from .utils import gen_xmltv_xml
# from .utils import getNFLTeams

from .espn_api import ESPN_API


class KemoAPI(ESPN_API):
    """
    REST API Wrapper for Kemo/Lemo TV

    Example Usage:
    from plexarr import KemoAPI
    from rich import print

    kemo = KemoAPI()
    for stream in kemo.getStreamsNFL():
        info = {
            "tvg_id": stream.get("stream_id"),
            "tvg_name": stream.get("name").split(":")[0].strip(),
            "tvg_logo": stream.get("stream_icon"),
            "epg_desc": stream.get("name").split(":", maxsplit=1)[1].strip(),
        }
        print(info)
    """

    def __init__(self):
        """Configs"""
        config = ConfigParser()
        config.read(Path(Path.home(), '.config/plexarr.ini'))

        self.API_URL = config["kemo"].get('api_url')
        self.USERNAME = config["kemo"].get('username')
        self.PASSWORD = config["kemo"].get('password')
        self.PARAMS = {
            "username": self.USERNAME,
            "password": self.PASSWORD
        }
        self.CATEGORY = {}
        self.STREAMS = {}
        super().__init__()

    def getCategories(self, groups):
        """Get All Categories in Matching Groups"""
        payload = self.PARAMS
        payload.update({'action': 'get_live_categories'})
        r = requests.get(url=self.API_URL, params=payload)
        return list(filter(lambda x: x["category_name"] in groups, r.json()))

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
        streams = self.getStreams(terms="USA NFL Sunday 7")
        return streams

    def getStreamsNBA(self):
        """Get NBA Streams"""
        self.setCategory(query="NBA")
        streams_1 = self.getStreams(terms="USA NBA 0")
        streams_2 = self.getStreams(terms="USA NBA 1")
        streams = chain(streams_1, streams_2)
        return streams

    def getStreamsESPN(self, terms=""):
        """GET ESPN PLUS STREAMS"""
        self.setCategory(query="ESPN")
        streams = self.getStreams(terms=terms)
        return streams


    def m3uNFL(self):
        """Generate m3u for NFL Streams"""
        m3u = "#EXTM3U\n"
        tvg_cuid = 705
        for i, stream in enumerate(self.getStreamsNFL()):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/d7a1c666d3827922b7dfb5fbb9a3b450.png"
            tvg_group = "NFL Sunday Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uNBA(self):
        """Generate m3u for NBA Streams"""
        m3u = "#EXTM3U\n"
        tvg_cuid = 100
        for i, stream in enumerate(self.getStreamsNBA()):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/118ae626674246e6d081a4ff16921b19.png"
            tvg_group = "NBA Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uESPN(self, terms=""):
        """Generate m3u for ESPN PLUS Streams"""
        m3u = "#EXTM3U\n"
        tvg_cuid = 1500
        for i, stream in enumerate(self.getStreamsESPN(terms=terms)):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "https://artwork.espncdn.com/programs/14ef54cc-6fd8-443d-80b8-365c1f64d606/16x9/large_20211213222642.jpg"
            tvg_group = "ESPN+"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def xmlNFL(self):
        """Generate xml for NFL Streams"""
        nfl_teams = self.getNFLTeams()
        regex = (
            rf"(?P<tvg_name>\w+\s+\w+\s+\w+\s+(\d+|\w+))(\s|:)*"
            rf"(?P<team1>(?:{teams}))*(\svs\s+)*"
            rf"(?P<team2>(?:{teams}))*(\s*@\s*|\s*\(\s*)*"
            rf"(?P<time>\d+:\d+\s*\w+)*(\)|)*"
        )
        m = re.compile(regex)
        channels = []
        programs = []
        for stream in self.getStreamsNFL():
            tvg_id = stream.get("stream_id")

            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/d7a1c666d3827922b7dfb5fbb9a3b450.png"
            # tvg_group = "NFL Sunday Games"

            epg_desc = stream.get("name").split(":", maxsplit=1)[1].strip()
            # if epg_desc := stream.get("name").split(":", maxsplit=1)[1].strip():
            if epg_desc:
                try:
                    epg_title = epg_desc.split('@')[0].strip()
                    date_now = getEPGTimeNow(dt_obj=True).date()
                    game_time = epg_desc.split('@')[1].strip()
                    if date_now.weekday() == 6:
                        game_datetime = pd.to_datetime(f'{date_now} {game_time}')
                    else:
                        game_datetime = pd.to_datetime(f'{(getEPGTimeNow(dt_obj=True) + Week(weekday=6)).date()} {game_time}')
                    epg_start = convertEPGTime(game_datetime.tz_localize('US/Eastern'), epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

                    if ((date_now - game_datetime.date()).days < 5):
                        channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                        programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})
                except Exception:
                    try:
                        epg_title = epg_desc.split('@')[0].strip()
                        date_now = getEPGTimeNow(dt_obj=True).date()
                        game_time = epg_desc.split('(')[1].split('ET')[0].strip().replace(" p", ":00 p")
                        if date_now.weekday() == 6:
                            game_datetime = pd.to_datetime(f'{date_now} {game_time}')
                        else:
                            game_datetime = pd.to_datetime(f'{(getEPGTimeNow(dt_obj=True) + Week(weekday=6)).date()} {game_time}')
                        epg_start = convertEPGTime(game_datetime.tz_localize('US/Eastern'), epg_fmt=True)
                        epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

                        if ((date_now - game_datetime.date()).days < 5):
                            channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                            programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})

                    except Exception:
                        pass

        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)

    def xmlNBA(self):
        """Generate xml NBA Streams"""
        channels = []
        programs = []
        for stream in self.getStreamsNBA():
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/118ae626674246e6d081a4ff16921b19.png"
            # tvg_group = "NBA Games"

            epg_desc = stream.get("name").split(":", maxsplit=1)[1].strip()
            # if epg_desc := stream.get("name").split(":", maxsplit=1)[1].strip():
            if epg_desc:
                try:
                    epg_title = epg_desc.split('@')[0].strip()
                    date_now = getEPGTimeNow(dt_obj=True).date()
                    game_time = epg_desc.split('@')[1].strip()
                    game_datetime = pd.to_datetime(f'{date_now} {game_time}')
                    epg_start = convertEPGTime(game_datetime.tz_localize('US/Eastern'), epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

                    if ((date_now - game_datetime.date()).days < 5):
                        channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                        programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})

                except Exception:
                    pass
        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)

    def xmlESPN(self, terms=""):
        """Generate xml NBA Streams"""
        channels = []
        programs = []
        for stream in self.getStreamsESPN(terms=terms):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "https://artwork.espncdn.com/programs/14ef54cc-6fd8-443d-80b8-365c1f64d606/16x9/large_20211213222642.jpg"
            # tvg_group = "ESPN+"

            epg_desc = stream.get("name").split(":", maxsplit=1)[1].strip()
            # if epg_desc := stream.get("name").split(":", maxsplit=1)[1].strip():
            if epg_desc:
                try:
                    epg_title = epg_desc.split('  ')[0].strip()
                    date_now = getEPGTimeNow(dt_obj=True).date()
                    game_time = epg_desc.split('  ')[1].split('et')[0].strip()
                    game_datetime = pd.to_datetime(f'{date_now} {game_time}')
                    epg_start = convertEPGTime(game_datetime.tz_localize('US/Eastern'), epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

                    if ((date_now - game_datetime.date()).days < 5):
                        channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                        programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})
                except Exception:
                    pass
        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)
