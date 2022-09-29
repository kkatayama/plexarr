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
        # self.API_URL = "http://data.nba.net/10s/prod/v1/today.json"
        self.API_URL = "http://data.nba.net/prod/v2/today.json"
        self.PATHS = self.getURL(self.API_URL).get("links")
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

        path_teams = self.PATHS.get('teams')
        teams = []
        for item in self.get(path_teams)["league"]["standard"]:
            team = {
                "team_name": item["fullName"],
                "team_id": item["teamId"],
                "team_nick": item["nickname"],
                "team_abbr": item["tricode"],
                "team_area": item["city"]
            }
            teams.append(team)
        return teams
