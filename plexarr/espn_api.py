from .utils import to_csv, read_csv
from datetime import datetime as dt
from pathlib import Path
from rich import print
from furl import furl
import pandas as pd
import requests
import json
import re


class ESPN_API(object):
    """REST API Wrapper for GitHub"""

    def __init__(self, load=True):
        """Endpoints: https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c"""
        self.PARAMS = {'lang': 'en', 'region': 'us', 'limit': 32}
        self.YEAR = self.getYear()
        self.API_URL = "http://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
        if load:
            self.df_teams = self.getNFLTeams()
            if not Path(__file__).parent.joinpath(f'data/nfl_schedule_{self.YEAR}.csv').exists():
                self.getNFLSchedule()

    def getYear(self):
        """get NFL season start year"""
        today = dt.now()
        # year = (today.year - 1) if (today.month < 3) else today.year
        # Season starts in September and ends in January...
        year = (today.year - 1) if (today.month < 8) else today.year
        return year

    def get(self, path='/', data={}):
        """Requests GET Wrapper"""
        params = self.PARAMS
        params.update(data)

        url = furl(self.API_URL.strip('/')+'/').join(path.strip('/'))
        r = requests.get(url=url, params=params)
        return r.json()

    def getURL(self, url='', data={}):
        """Requests GET URL Wrapper"""
        params = self.PARAMS
        params.update(data)
        r = requests.get(url, params=params)
        return r.json()

    def getItems(self, path='/', data={}):
        """Requests Nested get(): [getURL()] Wrapper"""
        print(f'path = "{path}"')
        return [self.getURL(item["$ref"]) for item in self.get(path=path, data=data)["items"]]

    def getNFLTeams(self, year=0, data={}, update=False):
        year = year if year else self.YEAR

        # -- read cached data if exists: plexarr/data/nfl_teams_2022.js
        csv = Path(__file__).parent.joinpath(f'data/nfl_teams_{year}.csv')
        if csv.exists() and not update:
            # print(f'loading from cache: "{csv}"')
            df_teams = read_csv(csv)
            # with open(str(js)) as f:
            #     teams = json.load(f)
        else:
            print(f'first run...\ncaching: "{csv}"')
            # --- get all team links
            data = data if data else self.PARAMS
            path = f'/seasons/{year}/teams'
            # ref_links = [item['$ref'] for item in self.get(path=path, data=data)['items']]

            # # -- fetch and parse all team links
            teams = []
            # for link in ref_links:
            #     team_info = self.getURL(url=link)
            for item in self.getItems(path=path, data=data):
                team = {
                    "team_name": item["displayName"],
                    "team_id": item["id"],
                    "team_nick": item["name"],
                    "team_abbr": item["abbreviation"],
                    "team_area": item["location"],
                    "team_venue": item["venue"]["fullName"]
                }
                teams.append(team)

            # -- sort teams
            teams = sorted(teams, key=lambda x: x["team_name"])
            df_teams = pd.DataFrame.from_records(teams)
            # -- cache team data
            # with open(str(js), 'w') as f:
            #     json.dump(teams, f, indent=2)
            to_csv(df_teams, csv)
        return df_teams

    def getNBATeams(self, year=0, data={}, update=False):
        back_up = str(self.API_URL)
        self.API_URL = 'http://sports.core.api.espn.com/v2/sports/basketball/leagues/nba'
        year = year if year else self.YEAR

        csv = Path(__file__).parent.joinpath(f'data/nba_teams_{year}.csv')
        if csv.exists() and not update:
            df_teams = read_csv(csv)
        else:
            print(f'first run...\ncaching: "{csv}"')
            data = data if data else self.PARAMS
            path = f'/seasons/{year}/teams'
            teams = []
            for item in self.getItems(path=path, data=data):
                team = {
                    "team_nick": item["name"],
                    "team_name": item["displayName"],
                    "team_id": item["id"],
                    "team_abbr": item["abbreviation"],
                    "team_area": item["location"],
                    "team_venue": item["venue"]["fullName"]
                }
                teams.append(team)

            # -- sort teams
            teams = sorted(teams, key=lambda x: x["team_name"])
            df_teams = pd.DataFrame.from_records(teams)
            to_csv(df_teams, csv)
        # df_teams = df_teams[["team_name", "team_nick", "team_venue"]]
        self.API_URL = str(back_up)
        return df_teams


    def getNFLSchedule(self, year=0, data={}, update=False):
        year = year if year else self.YEAR

        # -- read cached data if exists: plexarr/data/nfl_teams_2022.js
        csv = Path(__file__).parent.joinpath(f'data/nfl_schedule_{year}.csv')
        if csv.exists() and not update:
            # print(f'loading from cache: "{csv}"')
            df_schedule = read_csv(csv)
            # with open(str(csv)) as f:
            #     teams = json.load(f)
        else:
            print(f'first run...\ncaching: "{csv}"')
            # -- fetch and parse all season types
            data = data if data else self.PARAMS
            path = f'/seasons/{year}/types'
            schedule = []
            for season in self.getItems(path=path, data=data):
                path_weeks = f'{path}/{season["id"]}/weeks'
                for week in self.getItems(path=path_weeks, data=data):
                    path_events = f'{path_weeks}/{week["number"]}/events'
                    for event in self.getItems(path=path_events, data=data):
                        df_event = pd.DataFrame.from_records([
                            {"team_id": team["id"], "homeAway": team["homeAway"]}
                            for team in event["competitions"][0]["competitors"]
                        ])
                        df_game = df_event.merge(self.df_teams)
                        home = df_game[df_game["homeAway"] == "home"].squeeze()
                        away = df_game[df_game["homeAway"] == "away"].squeeze()

                        game = {
                            "season": season["name"],
                            "season_type": season["id"],
                            "week_name": week["text"],
                            "week_start": week["startDate"],
                            "week_end": week["endDate"],
                            "game_name": event["name"],
                            "game_short": event["shortName"],
                            "game_date": event["date"],
                            "home_team": "" if home.empty else home["team_name"] ,
                            "home_venue": "" if home.empty else home["team_venue"],
                            "away_team": "" if away.empty else away["team_name"],
                        }
                        schedule.append(game)
            df_schedule = pd.DataFrame.from_records(schedule)
            df_schedule["week_start"] = pd.to_datetime(df_schedule["week_start"])
            df_schedule["week_end"] = pd.to_datetime(df_schedule["week_end"])
            df_schedule["game_date"] = pd.to_datetime(df_schedule["game_date"])
            to_csv(df_schedule, csv)
        return df_schedule

    def parseNFLInfo(self, line):
        """
        Parse NFL Info From Channel Name Description

        from plexarr.espn_api import ESPN_API
        from rich import print
        import re

        tests = [
            "USA NFL Sunday 705: Las Vegas Raiders vs Minnesota Vikings @ 04:25 PM",
            "USA NFL Sunday Night: Cincinnati Bengals vs Los Angeles Rams @ 06:30 PM",
            "USA NFL Sunday 705: Philadelphia Eagles vs  Cleveland Browns @ 01:00 PM",
            "USA NFL Sunday 706: New York Giants vs Cincinnati Bengals @ 07:00 PM",
            "USA NFL Sunday 707: Arizona Cardinals vs Baltimore Ravens @ 08:00 PM",
            "USA NFL Sunday 707: Arizona Cardinals vs Baltimore Ravens (08:00 PM)",
            "USA NFL Sunday 708:",
            "USA NFL Sunday 708",
        ]
        espn = ESPN_API()
        # teams = "|".join([team["team_name"] for team in espn.getNFLTeams()])
        # regex = rf"(?P<channel>\w+\s+\w+\s+\w+\s+(\d+|\w+))(\s|:)*(?P<team1>(?:{teams}))*(\svs\s+)*(?P<team2>(?:{teams}))*(\s*@\s*|\s*\(\s*)*(?P<time>\d+:\d+\s*\w+)*(\)|)*"
        # m = re.compile(regex)
        nfl_teams = "|".join(espn.getNFLTeams().team_name.values)
        regex = rf'(?P<tvg_name>[\w\s]+)[:]\s+(?P<team1>({nfl_teams}))[vsat\s]*(?P<team2>({nfl_teams}))[\s@]+(?P<time>[\d:]+\s*[AMP]*)'
        for test in tests:
            print(test)
            print(re.search(regex, line, flags=re.IGNORECASE).groupdict())

        # -- OUTPUTS -- #
        loading from cache: "/Users/katayama/.pyenv/versions/3.9.1/lib/python3.9/site-packages/plexarr/data/nfl_teams_2022.js"
        USA NFL Sunday 705: Las Vegas Raiders vs Minnesota Vikings @ 04:25 PM
        {'channel': 'USA NFL Sunday 705', 'team1': 'Las Vegas Raiders', 'team2': 'Minnesota Vikings', 'time': '04:25 PM'}
        USA NFL Sunday Night: Cincinnati Bengals vs Los Angeles Rams @ 06:30 PM
        {'channel': 'USA NFL Sunday Night', 'team1': 'Cincinnati Bengals', 'team2': 'Los Angeles Rams', 'time': '06:30 PM'}
        USA NFL Sunday 705: Philadelphia Eagles vs  Cleveland Browns @ 01:00 PM
        {'channel': 'USA NFL Sunday 705', 'team1': 'Philadelphia Eagles', 'team2': 'Cleveland Browns', 'time': '01:00 PM'}
        USA NFL Sunday 706: New York Giants vs Cincinnati Bengals @ 07:00 PM
        {'channel': 'USA NFL Sunday 706', 'team1': 'New York Giants', 'team2': 'Cincinnati Bengals', 'time': '07:00 PM'}
        USA NFL Sunday 707: Arizona Cardinals vs Baltimore Ravens @ 08:00 PM
        {'channel': 'USA NFL Sunday 707', 'team1': 'Arizona Cardinals', 'team2': 'Baltimore Ravens', 'time': '08:00 PM'}
        USA NFL Sunday 707: Arizona Cardinals vs Baltimore Ravens (08:00 PM)
        {'channel': 'USA NFL Sunday 707', 'team1': 'Arizona Cardinals', 'team2': 'Baltimore Ravens', 'time': '08:00 PM'}
        USA NFL Sunday 708:
        {'channel': 'USA NFL Sunday 708', 'team1': None, 'team2': None, 'time': None}
        USA NFL Sunday 708
        {'channel': 'USA NFL Sunday 708', 'team1': None, 'team2': None, 'time': None}
        """
        # nfl_teams = "|".join([team["team_name"] for team in self.NFL_TEAMS])
        #nfl_teams = "|".join(self.df_teams["team_name"])

        # regex = (
        #     rf"(?P<tvg_name>\w+\s+\w+\s+\w+\s+(\d+|\w+))(\s|:)*"
        #     rf"(?P<team1>(?:{nfl_teams}))*(\svs\s+)*"
        #     rf"(?P<team2>(?:{nfl_teams}))*(\s*@\s*|\s*\(\s*)*"
        #     rf"(?P<time>\d+:\d+\s*\w+)*(\)|)*"
        # )
        # m = re.compile(regex. re.IGNORECASE)
        # return m.search(line).groupdict()

        nfl_teams = "|".join(self.df_teams.team_name.values)
        regex = rf'(?P<tvg_name>[\w\s]+)[:]\s+(?P<team1>({nfl_teams}))[vsat\s]*(?P<team2>({nfl_teams}))[\s@]+(?P<time>[\d:]+\s*[AMP]*)'
        return re.search(regex, line, flags=re.IGNORECASE).groupdict()
