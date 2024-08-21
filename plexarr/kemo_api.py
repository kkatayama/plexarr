from configparser import ConfigParser
from itertools import chain
from pathlib import Path
import json
import re

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
from .nba_api import NBA_API



class KemoAPI(object):
    """
    REST API Wrapper for Kemo/Lemo TV


    Example NFL Usage:

    from plexarr.kemo_api import KemoAPI
    from plexarr.espn_api import ESPN_API
    from plexarr.utils import getEPGTimeNow, convertEPGTime
    from rich import print
    import pandas as pd


    kemo = KemoAPI()
    espn = ESPN_API()
    date_now = getEPGTimeNow(dt_obj=True)
    for stream in kemo.getStreamsNFL():
        tvg_id = stream.get("stream_id")
        tvg_name = stream.get("name").split(":")[0].strip()
        tvg_logo = "http://line.lemotv.cc/images/d7a1c666d3827922b7dfb5fbb9a3b450.png"
        epg_info = stream.get("name").split(":", maxsplit=1)
        try:
            epg_desc = epg_info[1].strip()

            if epg_desc:
                print(epg_desc)
                nfl_info = espn.parseNFLInfo(stream.get("name"))
                ds_teams = [nfl_info["team1"], nfl_info["team2"]]
                df_sched = espn.getNFLSchedule()
                df_week = df_sched[((df_sched["week_start"] <= date_now) & (date_now <= df_sched["week_end"]))]
                try:
                    df_game = df_week[(df_week["home_team"].isin(ds_teams) & df_week["away_team"].isin(ds_teams))].iloc[0]
                except Exception:
                    dt_now = convertEPGTime(pd.to_datetime(date_now) - pd.DateOffset(hours=6), dt_obj=True)
                    df_week = df_sched[((df_sched["day_start"] <= dt_now) & (dt_now <= df_sched["day_end"]))]
                    df_game = df_week[(df_week["home_team"].isin(ds_teams) & df_week["away_team"].isin(ds_teams))].iloc[0]

                epg_title = f'{df_game.home_team} vs {df_game.away_team} at {df_game.home_venue}'
                epg_start = convertEPGTime(df_game.game_date, epg_fmt=True)
                epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

                print({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
                print({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})
        except Exception as e:
            print(stream)

    Example NBA Usage:

    from plexarr.kemo_api import KemoAPI
    from plexarr.nba_api import NBA_API
    from plexarr.utils import getEPGTimeNow, convertEPGTime
    from rich import print
    import pandas as pd


    kemo = KemoAPI()
    nba = NBA_API()
    date_now = getEPGTimeNow(dt_obj=True)
    for stream in kemo.getStreamsNBA():
        tvg_id = stream.get("stream_id")
        tvg_name = stream.get("name").split(":")[0].strip()
        tvg_logo = "http://line.lemotv.cc/images/118ae626674246e6d081a4ff16921b19.png"
        epg_info = stream.get("name").split(":", maxsplit=1)
        epg_desc = epg_info[1].strip()

        if epg_desc:
            nba_info = nba.parseNBAInfo(stream.get("name"))
            ds_teams = [nba_info["team1"], nba_info["team2"]]
            df_sched = nba.getNBASchedule()
            df_date = df_sched[((df_sched["day_start"] <= date_now) & (date_now <= df_sched["day_end"]))]
            try:
                df_game = df_date[(df_date["home_team"].isin(ds_teams) & df_date["away_team"].isin(ds_teams))].iloc[0]
            except Exception:
                dt_now = convertEPGTime(pd.to_datetime(date_now) - pd.DateOffset(hours=6), dt_obj=True)
                df_date = df_sched[((df_sched["day_start"] <= dt_now) & (dt_now <= df_sched["day_end"]))]
                df_game = df_date[(df_date["home_team"].isin(ds_teams) & df_date["away_team"].isin(ds_teams))].iloc[0]

            epg_title = f'{df_game.home_team} vs {df_game.away_team} at {df_game.home_venue}'
            epg_start = convertEPGTime(df_game.game_time, epg_fmt=True)
            epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

            print({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
            print({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})
    """

    def __init__(self, iptv='lemo', nba=False, wnba=False):
        """Configs"""
        config = ConfigParser()
        config.read(Path(Path.home(), '.config/plexarr.ini'))
        conf = dict(config[iptv].items())
        self.API_URL = conf.get("api_url")
        self.USERNAME = conf.get("username")
        self.PASSWORD = conf.get("password")
        self.PARAMS = {"username": self.USERNAME, "password": self.PASSWORD}
        self.CATEGORY = {}
        self.STREAMS = {}
        self.espn = ESPN_API(wnba=wnba)
        self.nba = NBA_API()

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

    def getStreams(self, terms=''):
        """Get Streams by Category_ID and filtered by 'terms'"""
        payload = self.PARAMS
        payload.update({'action': 'get_live_streams'})
        payload.update({'category_id': self.CATEGORY.get("category_id")})
        r = requests.get(url=self.API_URL, params=payload)
        streams = r.json()

        if isinstance(terms, str):
            return (stream for stream in streams if terms.lower() in stream.get('name').lower())
        if isinstance(terms, list):
            all_streams = []
            for term in terms:
                all_streams += [stream for stream in streams if term.lower() in stream.get('name').lower()]
            return all_streams
        return streams

    def getEPG(self, stream_id=0):
        """Get All EPG for Live Stream"""
        payload = self.PARAMS
        payload.update({'action': 'get_simple_data_table'})
        payload.update({'stream_id': stream_id})
        r = requests.get(url=self.API_URL, params=payload)
        return r.json()

    def getStreamsNFL(self):
        """Get NFL Streams"""
        self.setCategory(query="NFL")
        terms = ["USA NFL Thursday Night", "USA NFL Sunday Night", "USA NFL Monday Night", "USA NFL Sunday 7"]
        streams = self.getStreams(terms=terms)
        return streams

    def loadStreamsNBA(self, t_streams=[]):
        nba_streams_cached = Path(__file__).parent.joinpath(f'data/nba_streams.json')
        if nba_streams_cached.exists():
            return json.load(nba_streams_cached.open())
            # json.dump(streams, nba_streams_cached.open('w'))
        self.saveStreamsNBA(t_streams=t_streams)
        return json.load(nba_streams_cached.open())

    def saveStreamsNBA(self, t_streams=[]):
        nba_streams_cached = Path(__file__).parent.joinpath(f'data/nba_streams.json')
        nba_streams = []
        for stream in t_streams.copy():
            s = stream.copy()
            s["name"] = s.get("name", "").split(':')[0].strip()
            nba_streams.append(s)
        json.dump(nba_streams, nba_streams_cached.open('w'))

    def getStreamsNBA(self):
        """Get NBA Streams"""
        self.setCategory(query="NBA")
        """
        streams_1 = self.getStreams(terms="USA NBA 0")
        streams_2 = self.getStreams(terms="USA NBA 1")
        streams = chain(streams_1, streams_2)
        """
        nba_all = [f'USA NBA {str(i).zfill(2)}' for i in range(1, 19)]
        streams = self.getStreams(terms=nba_all)
        nba_streams = self.loadStreamsNBA(t_streams=streams)
        if len(streams) < len(nba_streams):
            temp_streams = streams.copy()
            streams = []
            for name in nba_all:
                stream = next((s for s in temp_streams if name in s["name"]), {})
                if not stream:
                    stream = next((s for s in nba_streams if name in s["name"]), {})
                streams.append(stream)
        self.saveStreamsNBA(t_streams=streams)
        return streams

    def loadStreamsWNBA(self, t_streams=[]):
        wnba_streams_cached = Path(__file__).parent.joinpath(f'data/wnba_streams.json')
        if wnba_streams_cached.exists():
            return json.load(wnba_streams_cached.open())
            # json.dump(streams, wnba_streams_cached.open('w'))
        self.saveStreamsWNBA(t_streams=t_streams)
        return json.load(wnba_streams_cached.open())

    def saveStreamsWNBA(self, t_streams=[]):
        wnba_streams_cached = Path(__file__).parent.joinpath(f'data/wnba_streams.json')
        wnba_streams = []
        for stream in t_streams.copy():
            s = stream.copy()
            s["name"] = s.get("name", "").split(':')[0].strip()
            wnba_streams.append(s)
        json.dump(wnba_streams, wnba_streams_cached.open('w'))

    def getStreamsWNBA(self):
        """Get WNBA Streams"""
        self.setCategory(query="WNBA")
        """
        streams_1 = self.getStreams(terms="USA WNBA 0")
        streams_2 = self.getStreams(terms="USA WNBA 1")
        streams = chain(streams_1, streams_2)
        """
        wnba_all = [f'WNBA {str(i).zfill(2)}' for i in range(1, 6)]
        streams = self.getStreams(terms=wnba_all)
        wnba_streams = self.loadStreamsWNBA(t_streams=streams)
        if len(streams) < len(wnba_streams):
            temp_streams = streams.copy()
            streams = []
            for name in wnba_all:
                stream = next((s for s in temp_streams if name in s["name"]), {})
                if not stream:
                    stream = next((s for s in wnba_streams if name in s["name"]), {})
                streams.append(stream)
        self.saveStreamsWNBA(t_streams=streams)
        return streams

    def getStreamsNCAAB(self):
        """Get NCAAB Mens"""
        self.setCategory(query="NCAA Men")
        terms = ["NCAAB"]
        streams = self.getStreams(terms=terms)
        return streams

    def getStreamsNCAAW(self):
        """Get NCAAW Womens"""
        self.setCategory(query="NCAA Women")
        terms = ["NCAAW"]
        streams = self.getStreams(terms=terms)
        return streams

    def getStreamsESPN(self, terms=""):
        """GET ESPN PLUS STREAMS"""
        self.setCategory(query="ESPN")
        streams = self.getStreams(terms=terms)
        return streams

    def m3uNFL(self, tvg_cuid=702):
        """Generate m3u for NFL Streams"""
        m3u = "#EXTM3U\n"
        for i, stream in enumerate(self.getStreamsNFL()):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/d7a1c666d3827922b7dfb5fbb9a3b450.png"
            tvg_group = "NFL Sunday Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uNBA(self, tvg_cuid=801):
        """Generate m3u for NBA Streams"""
        m3u = "#EXTM3U\n"
        for i, stream in enumerate(self.getStreamsNBA()):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/118ae626674246e6d081a4ff16921b19.png"
            tvg_group = "NBA Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uNCAAB(self, tvg_cuid=240):
        """Generate m3u for NCAAB Streams"""
        m3u = "#EXTM3U\n"
        for i, stream in enumerate(self.getStreamsNCAAB()):
            tvg_id = stream.get("stream_id")
            # tvg_name = stream.get("name").split(":")[0].strip()
            tvg_name = re.search(r'(NCAAB \d+)', stream.get("name")).group()
            tvg_logo = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/March_Madness_logo.svg/250px-March_Madness_logo.svg.png"
            tvg_group = "NCAAB Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uNCAAW(self, tvg_cuid=260):
        """Generate m3u for NCAAB Streams"""
        m3u = "#EXTM3U\n"
        for i, stream in enumerate(self.getStreamsNCAAW()):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            # tvg_name = re.search(r'(NCAAW B \d+)', stream.get("name")).group()
            tvg_logo = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/March_Madness_logo.svg/250px-March_Madness_logo.svg.png"
            tvg_group = "NCAAW Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uWNBA(self, tvg_cuid=13):
        """Generate m3u for NBA Streams"""
        m3u = "#EXTM3U\n"
        for i, stream in enumerate(self.getStreamsWNBA()):
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "https://i0.wp.com/winsidr.com/wp-content/uploads/2023/05/WNBALogo_1997.png?resize=300%2C300&ssl=1"
            tvg_group = "WNBA Games"

            m3u += f'#EXTINF:-1 CUID="{tvg_cuid}" tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{tvg_group}",{tvg_name}\n'
            m3u += self.API_URL.replace('/player_api.php', f'/{self.USERNAME}/{self.PASSWORD}/{tvg_id}\n')
            tvg_cuid += 1
        return m3u

    def m3uESPN(self, terms="", tvg_cuid=1500):
        """Generate m3u for ESPN PLUS Streams"""
        m3u = "#EXTM3U\n"
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
        channels = []
        programs = []
        date_now = getEPGTimeNow(dt_obj=True)
        for stream in self.getStreamsNFL():
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/d7a1c666d3827922b7dfb5fbb9a3b450.png"
            # tvg_group = "NFL Sunday Games"

            epg_info = stream.get("name").split(":", maxsplit=1)
            try:
                epg_desc = epg_info[1].strip()
                # if epg_desc := stream.get("name").split(":", maxsplit=1)[1].strip():
                if epg_desc:
                    try:
                        nfl_info = self.espn.parseNFLInfo(stream.get("name"))
                        ds_teams = [nfl_info["team1"], nfl_info["team2"]]
                        df_sched = self.espn.getNFLSchedule()
                        df_week = df_sched[((df_sched["week_start"] <= date_now) & (date_now <= df_sched["week_end"]))]
                        df_game = df_week[(df_week["home_team"].isin(ds_teams) & df_week["away_team"].isin(ds_teams))].iloc[0]

                        epg_title = f'{df_game.home_team} vs {df_game.away_team} at {df_game.home_venue}'
                        epg_start = convertEPGTime(df_game.game_date, epg_fmt=True)
                        epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
                    except Exception as e:
                        print(e)
                        epg_title = "== PARSER FAILED =="
                        epg_desc = stream.get("name")
                        epg_start = getEPGTimeNow(epg_fmt=True)
                        epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
                else:
                    epg_title = "NO GAME RIGHT NOW?"
                    epg_desc = "OFF AIR"
                    epg_start = getEPGTimeNow(epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
            except Exception:
                epg_title = "NO GAME RIGHT NOW?"
                epg_desc = "OFF AIR (no description...)"
                epg_start = getEPGTimeNow(epg_fmt=True)
                epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

            channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
            programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})

        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)

    def xmlNBA(self):
        """Generate xml NBA Streams"""
        channels = []
        programs = []
        date_now = getEPGTimeNow(dt_obj=True)
        for stream in self.getStreamsNBA():
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "http://line.lemotv.cc/images/118ae626674246e6d081a4ff16921b19.png"
            # tvg_group = "NBA Games"

            epg_info = stream.get("name").split(":", maxsplit=1)
            try:
                epg_desc = epg_info[1].strip()
                if epg_desc:
                    try:
                        nba_info = self.nba.parseNBAInfo(stream.get("name"))
                        ds_teams = [nba_info["team1"], nba_info["team2"]]
                        df_sched = self.nba.getNBASchedule()
                        df_date = df_sched[((df_sched["day_start"] <= date_now) & (date_now <= df_sched["day_end"]))]
                        try:
                            df_game = df_date[(df_date["home_team"].isin(ds_teams) & df_date["away_team"].isin(ds_teams))].iloc[0]
                        except Exception:
                            dt_now = convertEPGTime(pd.to_datetime(date_now) - pd.DateOffset(hours=6), dt_obj=True)
                            df_date = df_sched[((df_sched["day_start"] <= dt_now) & (dt_now <= df_sched["day_end"]))]
                            df_game = df_date[(df_date["home_team"].isin(ds_teams) & df_date["away_team"].isin(ds_teams))].iloc[0]

                        epg_title = f'{df_game.home_team} vs {df_game.away_team} at {df_game.home_venue}'
                        epg_start = convertEPGTime(df_game.game_time, epg_fmt=True)
                        epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
                    except Exception:
                        epg_title = stream.get("name") # "== PARSER FAILED =="
                        epg_desc = stream.get("name")
                        epg_start = getEPGTimeNow(epg_fmt=True)
                        epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
                else:
                    epg_title = "NO GAME RIGHT NOW?"
                    epg_desc = "OFF AIR"
                    epg_start = getEPGTimeNow(epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
            except Exception:
                epg_title = "NO GAME RIGHT NOW?"
                epg_desc = "OFF AIR (no description...)"
                epg_start = getEPGTimeNow(epg_fmt=True)
                epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

            channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
            programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})

        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)

    def xmlNCAAB(self):
        """Generate NCAAB Streams"""
        channels = []
        programs = []
        date_now = getEPGTimeNow(dt_obj=True)
        for stream in self.getStreamsNCAAB():
            tvg_id = stream.get("stream_id")
            # tvg_name = stream.get("name").split(":")[0].strip()
            tvg_name = re.search(r'(NCAAB \d+)', stream.get("name")).group()
            tvg_logo = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/March_Madness_logo.svg/250px-March_Madness_logo.svg.png"
            # tvg_group = "NBA Games"

            # epg_info = stream.get("name").split("NCAAB ", maxsplit=1)
            epg_info = re.split(r'NCAAB \d+\s*', stream.get("name"), maxsplit=1)
            try:
                epg_desc = epg_info[1].strip()
                if epg_desc:
                    epg_title = stream.get("name") # "== PARSER FAILED =="
                    epg_desc = stream.get("name")
                    epg_start = getEPGTimeNow(epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
                else:
                    epg_title = "NO GAME RIGHT NOW?"
                    epg_desc = "OFF AIR"
                    epg_start = getEPGTimeNow(epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
            except Exception:
                epg_title = "NO GAME RIGHT NOW?"
                epg_desc = "OFF AIR (no description...)"
                epg_start = getEPGTimeNow(epg_fmt=True)
                epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

            channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
            programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})

        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)

    def xmlNCAAW(self):
        """Generate NCAAW Streams"""
        channels = []
        programs = []
        date_now = getEPGTimeNow(dt_obj=True)
        for stream in self.getStreamsNCAAW():
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            # tvg_name = re.search(r'(NCAAW B \d+)', stream.get("name")).group()
            tvg_logo = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/March_Madness_logo.svg/250px-March_Madness_logo.svg.png"

            epg_info = stream.get("name").split(":", maxsplit=1)
            # epg_info = re.split(r'NCAAW B \d+\s*', stream.get("name"), maxsplit=1)
            try:
                epg_desc = epg_info[1].strip()
                if epg_desc:
                    epg_title = stream.get("name") # "== PARSER FAILED =="
                    epg_desc = stream.get("name")
                    epg_start = getEPGTimeNow(epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
                else:
                    epg_title = "NO GAME RIGHT NOW?"
                    epg_desc = "OFF AIR"
                    epg_start = getEPGTimeNow(epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
            except Exception:
                epg_title = "NO GAME RIGHT NOW?"
                epg_desc = "OFF AIR (no description...)"
                epg_start = getEPGTimeNow(epg_fmt=True)
                epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

            channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
            programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})

        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)

    def xmlESPN(self, terms=""):
        """Generate xml NBA Streams"""
        channels = []
        programs = []
        date_now = getEPGTimeNow(dt_obj=True).date()
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


    def xmlWNBA(self):
        """Generate xml WNBA Streams (EPG)"""
        channels = []
        programs = []
        date_now = getEPGTimeNow(dt_obj=True)
        for stream in self.getStreamsWNBA():
            tvg_id = stream.get("stream_id")
            tvg_name = stream.get("name").split(":")[0].strip()
            tvg_logo = "https://i0.wp.com/winsidr.com/wp-content/uploads/2023/05/WNBALogo_1997.png?resize=300%2C300&ssl=1"
            # tvg_group = "WNBA Games"

            epg_info = stream.get("name").split(":", maxsplit=1)
            try:
                epg_desc = epg_info[1].strip()
                if epg_desc:
                    try:
                        wnba_info = self.espn.parseWNBAInfo(stream.get("name"))
                        ds_teams = [wnba_info["team1"], wnba_info["team2"]]
                        df_sched = self.espn.getWNBASchedule()
                        df_date = df_sched[((df_sched["day_start"] <= date_now) & (date_now <= df_sched["day_end"]))]
                        try:
                            df_game = df_date[(df_date["home_team"].isin(ds_teams) & df_date["away_team"].isin(ds_teams))].iloc[0]
                        except Exception:
                            dt_now = convertEPGTime(pd.to_datetime(date_now) - pd.DateOffset(hours=6), dt_obj=True)
                            df_date = df_sched[((df_sched["day_start"] <= dt_now) & (dt_now <= df_sched["day_end"]))]
                            df_game = df_date[(df_date["home_team"].isin(ds_teams) & df_date["away_team"].isin(ds_teams))].iloc[0]

                        epg_title = f'{df_game.home_team} vs {df_game.away_team} at {df_game.home_venue}'
                        epg_start = convertEPGTime(df_game.game_time, epg_fmt=True)
                        epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
                    except Exception:
                        epg_title = stream.get("name") # "== PARSER FAILED =="
                        epg_desc = stream.get("name")
                        epg_start = getEPGTimeNow(epg_fmt=True)
                        epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
                else:
                    epg_title = "NO GAME RIGHT NOW?"
                    epg_desc = "OFF AIR"
                    epg_start = getEPGTimeNow(epg_fmt=True)
                    epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)
            except Exception:
                epg_title = "NO GAME RIGHT NOW?"
                epg_desc = "OFF AIR (no description...)"
                epg_start = getEPGTimeNow(epg_fmt=True)
                epg_stop = convertEPGTime(pd.to_datetime(epg_start) + pd.DateOffset(hours=3), epg_fmt=True)

            channels.append({"tvg_id": tvg_id, "tvg_name": tvg_name, "tvg_logo": tvg_logo, "epg_desc": epg_desc})
            programs.append({"tvg_id": tvg_id, "epg_title": epg_title, "epg_start": epg_start, "epg_stop": epg_stop, "epg_desc": epg_desc})

        # return gen_xmltv_xml(channels=channels, programs=programs, url=self.API_URL)
        url = furl(self.API_URL).origin
        tpl = str(Path(__file__).parent.joinpath("templates/epg.tpl"))
        return template(tpl, channels=channels, programs=programs, url=url)
