from configparser import ConfigParser
from itertools import chain
from pathlib import Path

import pandas as pd
import requests
from pandas.tseries.offsets import Week
# from teddy import convertEPGTime, getEPGTimeNow
from .utils import convertEPGTime, getEPGTimeNow
from bottle import template
from furl import furl
# from .utils import gen_xmltv_xml
# from .utils import getNFLTeams

from .espn_api import ESPN_API


class KemoAPI(object):
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

        self.lemo = {
            "api_url": config["lemo"].get("api_url"),
            "username": config["lemo"].get("username"),
            "password": config["lemo"].get("password"),
            "params": {
                "username": config["lemo"].get("username"),
                "password": config["lemo"].get("password")
            },
        }
        self.lemo2 = {
            "api_url": config["lemo2"].get("api_url"),
            "username": config["lemo2"].get("username"),
            "password": config["lemo2"].get("password"),
            "params": {
                "username": config["lemo2"].get("username"),
                "password": config["lemo2"].get("password")
            },
        }
        self.CATEGORY = {}
        self.STREAMS = {}
        self.espn = ESPN_API()

    def getCategories(self, groups='', terms='', iptv='lemo'):
        """
        Get All Categories in Matching Groups

        ARGS:
            groups (str|list) - ex: "USA Sports" or ['USA News', 'USA Sports']
        """
        API_URL = eval(f'self.{iptv}["api_url"]')
        payload = eval(f'self.{iptv}["params"]')
        payload.update({'action': 'get_live_categories'})
        r = requests.get(url=API_URL, params=payload)

        if groups:
            return list(filter(lambda x: x["category_name"] in groups, r.json()))
        if terms:
            terms = [terms] if isinstance(terms, str) else terms
            return list(filter(lambda x: any(term in x["category_name"].lower() for term in terms), r.json()))
        return r.json()

    def getCategory(self, query='', iptv='lemo'):
        """Get Category using query filter"""
        API_URL = eval(f'self.{iptv}["api_url"]')
        payload = eval(f'self.{iptv}["params"]')
        payload.update({'action': 'get_live_categories'})
        r = requests.get(url=API_URL, params=payload)
        return next((cat for cat in r.json() if query.lower() in cat.get('category_name').lower()), {})

    def setCategory(self, query='', iptv='lemo'):
        """Set Category using 'query' filter"""
        API_URL = eval(f'self.{iptv}["api_url"]')
        payload = eval(f'self.{iptv}["params"]')
        payload.update({'action': 'get_live_categories'})
        r = requests.get(url=API_URL, params=payload)
        self.CATEGORY = next((cat for cat in r.json() if query.lower() in cat.get('category_name').lower()), {})

    def getStreams(self, terms='', iptv='lemo'):
        """Get Streams by Category_ID and filtered by 'terms'"""
        API_URL = eval(f'self.{iptv}["api_url"]')
        payload = eval(f'self.{iptv}["params"]')
        payload.update({'action': 'get_live_streams'})
        payload.update({'category_id': self.CATEGORY.get("category_id")})
        r = requests.get(url=API_URL, params=payload)
        streams = r.json()

        if isinstance(terms, str):
            return (stream for stream in streams if terms.lower() in stream.get('name').lower())
        if isinstance(terms, list):
            all_streams = []
            for term in terms:
                all_streams += [stream for stream in streams if term.lower() in stream.get('name').lower()]
            return all_streams
        return streams

    def getStreamsNFL(self, iptv='lemo'):
        """Get NFL Streams"""
        self.setCategory(query="NFL")
        terms = ["USA NFL Thursday Night", "USA NFL Sunday Night", "USA NFL Monday Night", "USA NFL Sunday 7"]
        streams = self.getStreams(terms=terms, iptv=iptv)
        return streams

    def getStreamsNBA(self, iptv='lemo'):
        """Get NBA Streams"""
        self.setCategory(query="NBA")
        streams_1 = self.getStreams(terms="USA NBA 0", iptv=iptv)
        streams_2 = self.getStreams(terms="USA NBA 1", iptv=iptv)
        streams = chain(streams_1, streams_2)
        return streams

    def getStreamsESPN(self, terms="", iptv='lemo'):
        """GET ESPN PLUS STREAMS"""
        self.setCategory(query="ESPN")
        streams = self.getStreams(terms=terms, iptv=iptv)
        return streams

    def m3uNFL(self, iptv='lemo'):
        """Generate m3u for NFL Streams"""
        API_URL = eval(f'self.{iptv}["api_url"]')
        USERNAME = eval(f'self.{iptv}["username"]')
        PASSWORD = eval(f'self.{iptv}["password"]')
        m3u = "#EXTM3U\n"
        tvg_cuid = 702
        for i, stream in enumerate(self.getStreamsNFL(iptv=iptv)):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/d7a1c666d3827922b7dfb5fbb9a3b450.png"
            tvg_group = "NFL Sunday Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += API_URL.replace('/player_api.php', f'/{USERNAME}/{PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uNBA(self, iptv='lemo'):
        """Generate m3u for NBA Streams"""
        API_URL = eval(f'self.{iptv}["api_url"]')
        USERNAME = eval(f'self.{iptv}["username"]')
        PASSWORD = eval(f'self.{iptv}["password"]')
        m3u = "#EXTM3U\n"
        tvg_cuid = 801
        for i, stream in enumerate(self.getStreamsNBA(iptv=iptv)):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/118ae626674246e6d081a4ff16921b19.png"
            tvg_group = "NBA Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += API_URL.replace('/player_api.php', f'/{USERNAME}/{PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uESPN(self, terms="", iptv='lemo'):
        """Generate m3u for ESPN PLUS Streams"""
        API_URL = eval(f'self.{iptv}["api_url"]')
        USERNAME = eval(f'self.{iptv}["username"]')
        PASSWORD = eval(f'self.{iptv}["password"]')
        m3u = "#EXTM3U\n"
        tvg_cuid = 1500
        for i, stream in enumerate(self.getStreamsESPN(terms=terms, iptv=iptv)):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "https://artwork.espncdn.com/programs/14ef54cc-6fd8-443d-80b8-365c1f64d606/16x9/large_20211213222642.jpg"
            tvg_group = "ESPN+"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += API_URL.replace('/player_api.php', f'/{USERNAME}/{PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def xmlNFL(self, iptv='lemo'):
        """Generate xml for NFL Streams"""
        API_URL = eval(f'self.{iptv}["api_url"]')
        channels = []
        programs = []
        for stream in self.getStreamsNFL(iptv=iptv):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/d7a1c666d3827922b7dfb5fbb9a3b450.png"
            # tvg_group = "NFL Sunday Games"

            epg_desc = stream.get("name").split(":", maxsplit=1)[1].strip()
            # if epg_desc := stream.get("name").split(":", maxsplit=1)[1].strip():
            if epg_desc:
                try:
                    nfl_info = self.espn.parseNFLInfo(stream.get("name"))
                    ds_teams = [nfl_info["team1"], nfl_info["team2"]]
                    df_sched = self.espn.getNFLSchedule()
                    date_now = getEPGTimeNow(dt_obj=True)
                    df_week = df_sched[((df_sched["week_start"] <= date_now) & (date_now <= df_sched["week_end"]))]
                    df_game = df_week[(df_week["home_team"].isin(ds_teams) & df_week["away_team"].isin(ds_teams))].iloc[0]

                    epg_title = f'{df_game.home_team} vs {df_game.away_team} at {df_game.home_venue}'
                    epg_start = convertEPGTime(df_game.game_date, epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

                    channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                    programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})
                except Exception:
                    pass
            else:
                try:
                    epg_desc = "OFF AIR"
                    date_now = getEPGTimeNow(dt_obj=True)
                    epg_title = "NO GAME RIGHT NOW?"
                    epg_start = getEPGTimeNow(epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

                    channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                    programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})
                except Exception:
                    pass

        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)

    def xmlNBA(self, iptv='lemo'):
        """Generate xml NBA Streams"""
        API_URL = eval(f'self.{iptv}["api_url"]')
        channels = []
        programs = []
        for stream in self.getStreamsNBA(iptv=iptv):
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
        url = furl(API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)

    def xmlESPN(self, terms="", iptv='lemo'):
        """Generate xml NBA Streams"""
        API_URL = eval(f'self.{iptv}["api_url"]')
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
        url = furl(API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)
