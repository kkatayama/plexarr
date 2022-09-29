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

    def getNBATeams(self):
        espn = ESPN_API(load=False)
        df_espn_teams = espn.getNBATeams(year=self.YEAR)

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
        df_teams.join(df_espn_teams.set_index('team_name'), on='team_name')
        return df_teams
