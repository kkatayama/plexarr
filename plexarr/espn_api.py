from datetime import datetime as dt
from pathlib import Path
from rich import print
from furl import furl
import requests
import json
import re


class ESPN_API(object):
    """REST API Wrapper for GitHub"""

    def __init__(self):
        """Endpoints: https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c"""
        self.API_URL = "http://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
        self.PARAMS = {'lang': 'en', 'region': 'us', 'limit': 32}
        self.YEAR = self.getYear()

    def getYear(self):
        """get NFL season start year"""
        today = dt.now()
        year = (today.year - 1) if (today.month < 3) else today.year
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

    def getNFLTeams(self, year=0, data={}, update=False):
        year = year if year else self.YEAR

        # -- read cached data if exists: plexarr/data/nfl_teams_2022.js
        js = Path(__file__).parent.joinpath(f'data/nfl_teams_{year}.js')
        if js.exists() and not update:
            print(f'loading from cache: "{js}"')
            with open(str(js)) as f:
                teams = json.load(f)
        else:
            # --- get all team links
            data = data if data else self.PARAMS
            path = f'/seasons/{year}/teams'
            team_links = [item['$ref'] for item in self.get(path=path, data=data)['items']]

            # -- fetch and parse all team links
            teams = []
            for link in team_links:
                team_info = self.getURL(url=link)
                team = {
                    "team_name": team_info["displayName"],
                    "team_id": team_info["id"],
                    "team_nick": team_info["name"],
                    "team_abbr": team_info["abbreviation"],
                    "team_area": team_info["location"],
                    "team_venue": team_info["venue"]["fullName"]
                }
                teams.append(team)

            # -- sort teams
            teams = sorted(teams, key=lambda x: x["team_name"])

            # -- cache team data
            with open(str(js), 'w') as f:
                json.dump(teams, f, indent=2)
        return teams

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
        teams = "|".join([team["team_name"] for team in espn.getNFLTeams()])
        regex = rf"(?P<channel>\w+\s+\w+\s+\w+\s+(\d+|\w+))(\s|:)*(?P<team1>(?:{teams}))*(\svs\s+)*(?P<team2>(?:{teams}))*(\s*@\s*|\s*\(\s*)*(?P<time>\d+:\d+\s*\w+)*(\)|)*"
        m = re.compile(regex)
        for test in tests:
            print(test)
            print(m.search(test).groupdict())

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
        nfl_teams = = "|".join([team["team_name"] for team in self.getNFLTeams()])
        regex = (
            rf"(?P<tvg_name>\w+\s+\w+\s+\w+\s+(\d+|\w+))(\s|:)*"
            rf"(?P<team1>(?:{nfl_teams}))*(\svs\s+)*"
            rf"(?P<team2>(?:{nfl_teams}))*(\s*@\s*|\s*\(\s*)*"
            rf"(?P<time>\d+:\d+\s*\w+)*(\)|)*"
        )
        m = re.compile(regex)
        return
