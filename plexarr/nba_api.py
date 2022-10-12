from .utils import to_csv, read_csv
from .espn_api import ESPN_API
from datetime import datetime as dt
from pathlib import Path
from rich import print
from furl import furl
import pandas as pd
import requests
import json
import re


class NBA_API(object):
    """REST API Wrapper for data.nba.net"""

    def __init__(self):
        """Endpoints: https://github.com/kshvmdn/nba.js/blob/master/docs/api/DATA.md"""
        self.API_URL = "http://data.nba.net"
        self.YEAR = self.getYear()
        self.df_teams = self.getNBATeams()


    def get(self, path='/'):
        """Requests GET Wrapper"""
        url = furl(self.API_URL.strip('/')+'/').join(path)
        r = requests.get(url=url)
        return r.json()

    def getURL(self, url=''):
        """Requests GET URL Wrapper"""
        r = requests.get(url)
        return r.json()

    def getYear(self):
        """get NBA season start year"""
        today = dt.now()
        year = (today.year - 1) if (today.month < 3) else today.year
        return year

    def getNBATeams(self, year=0):
        espn = ESPN_API(load=False)
        df_espn_teams = espn.getNBATeams(year=self.YEAR)

        year = year if year else self.YEAR
        path_teams = f'/prod/v2/{self.YEAR}/teams.json'
        teams = []
        for item in self.get(path_teams)["league"]["vegas"]:
            team = {
                "team_name": item["fullName"],
                "team_id": item["teamId"],
                "team_nick": item["nickname"],
                "team_abbr": item["tricode"],
                "team_area": item["city"]
            }
            teams.append(team)
        df_teams = pd.DataFrame.from_records(teams)
        df_teams = df_teams.join(df_espn_teams.set_index('team_name'), on='team_name')

        teams = []
        for item in self.get(path_teams)["league"]["standard"]:
            if item["fullName"] not in df_teams["team_name"].values:
                teams.append({
                    "team_name": item["fullName"],
                    "team_id": item["teamId"],
                    "team_nick": item["nickname"],
                    "team_abbr": item["tricode"],
                    "team_area": item["city"],
                    "team_venue": "overseas"
                })
        return pd.concat([df_teams, pd.DataFrame.from_records(teams)])

    def getNBASchedule(self, year=0, update=False):
        df_teams = self.df_teams
        year = year if year else self.YEAR
        path_schedule = f'/prod/v2/{year}/schedule.json'
        csv = Path(__file__).parent.joinpath(f'data/nba_schedule_{year}.csv')
        if csv.exists() and not update:
            df_schedule = read_csv(csv)
        else:
            schedule = []
            for event in self.get(path=path_schedule)["league"]["standard"]:
                game_time = pd.to_datetime(event["startTimeUTC"]).tz_convert(tz='US/Eastern')
                home = df_teams[df_teams["team_id"] == event["hTeam"]["teamId"]].squeeze()
                away = df_teams[df_teams["team_id"] == event["vTeam"]["teamId"]].squeeze()
                game = {
                    "day_start": game_time.replace(hour=0, minute=0, second=0),
                    "day_end": game_time.replace(hour=23, minute=59, second=59),
                    "game_time": game_time,
                    "home_team": "" if home.empty else home["team_name"] ,
                    "home_venue": "" if home.empty else home["team_venue"],
                    "away_team": "" if away.empty else away["team_name"],
                }
                schedule.append(game)
            df_schedule = pd.DataFrame.from_records(schedule)
        return df_schedule

    def parseNBAInfo(self, line):
        """
        from plexarr.nba_api import NBA_API
        from rich import print
        import re

        nba = NBA_API()
        tests = [
            "USA NBA 01: Miami Heat vs Boston Celtics @ 08:30 PM",
            "USA NBA 02: Miami Heat vs Boston Celtics @ 08:30 PM",
            "USA NBA 01: Oklahoma City Thunder vs Detroit Pistons @ 07:00 PM",
            "USA NBA 02: Memphis Grizzlies vs Orlando Magic @ 07:00 PM",
            "USA NBA 03: Memphis Grizzlies vs Orlando Magic @ 07:00 PM",
            "USA NBA 04: Milwaukee Bucks vs Chicago Bulls @ 08:00 PM",
            "USA NBA 05: San Antonio Spurs vs Utah Jazz @ 09:00 PM",
            "USA NBA 06: Portland Trail Blazers vs Golden State Warriors @ 10:00 PM"
        ]
        nba_teams = "|".join(nba.df_teams.team_name.values)
        regex = rf'(?P<tvg_name>[\w\s]+)[:]\s+(?P<team1>({nba_teams}))[vs\s]*(?P<team2>({nba_teams}))[\s@]+(?P<time>[\d:]+\s*[AMP]*)'
        for line in tests:
            print(re.search(regex, line, flags=re.IGNORECASE).groupdict())
        """
        nba_teams = "|".join(self.df_teams.team_name.values)
        regex = rf'(?P<tvg_name>[\w\s]+)[:]\s+(?P<team1>({nba_teams}))[vsat\s]*(?P<team2>({nba_teams}))[\s@]+(?P<time>[\d:]+\s*[AMP]*)'
        return re.search(regex, line, flags=re.IGNORECASE).groupdict()
