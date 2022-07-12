# coding: utf-8
from configparser import ConfigParser
from pathlib import Path
from urllib.parse import urljoin
import requests
import re


class uTorrentAPI(object):
    """REST API Wrapper for uTorrent"""

    def __init__(self):
        """Configs"""
        config = ConfigParser()
        config.read(Path(Path.home(), ".config/plexarr.ini"))

        self.api_url = config["utorrent"].get("api_url").strip("/") + "/"
        self.api_key = config["utorrent"].get("api_key")
        self.headers = {"Authorization": f"Basic {self.api_key}"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def getToken(self):
        """Get Token and Cookie Session"""
        url = urljoin(self.api_url, "token.html")
        s = self.session.get(url=url)
        regex = r"<div.*>(?P<token>.+)</div>"
        r = re.search(regex, s.text)
        if r:
            token = r.groupdict()["token"]
        else:
        token = s.text
        self.token = token
        return token

    def get(self, path="", data={}):
        """Session GET Wrapper"""
        data.update({"token": self.token})
        url = urljoin(self.api_url, path)
        s = self.session.get(url=url, params=data)
        return s.json()

    def getSettings(self):
        """Get uTorrent Web Settings"""
        data = {"action": "getsettings"}
        return self.get(data=data)

    def getTorrents(self):
        """Get List of Torrents"""
        data = {"list": 1}
        res = self.get(data=data)
        keys = [
            "torrent_hash",
            "torrent_status",
            "torrent_name",
            "torrent_size",
            "torrent_progress",
            "torrent_downloaded",
            "torrent_uploaded",
            "torrent_ratio",
            "torrent_upspeed",
            "torrent_downspeed",
            "torrent_eta",
            "torrent_label",
            "torrent_peers_connected",
            "torrent_peers_swarm",
            "torrent_seeds_connected",
            "torrent_seeds_swarm",
            "torrent_availability",
            "torrent_queue_position",
            "torrent_remaining",
            "torrent_download_url",
            "torrent_rss_feed_url",
            "torrent_status_message",
            "torrent_stream_id",
            "torrent_date_added",
            "torrent_date_completed",
            "torrent_app_update_url",
            "torrent_save_path",
            "unknown_1",
            "unknown_2",
            "unknown_3",
        ]
        for i, torrent in enumerate(res["torrents"]):
            res["torrents"][i] = dict(zip(keys, torrent))
        return res            

    def addMagnet(self, magnet_url=""):
        """Add Magnet URL
        Args:
            magnet_url (str): The magnet url of the torrent "magnet:..."
        """
        data = {"action": "add-url", "s": magnet_url}
        return self.get(data=data)

    def setLabel(self, torrent_hash="", label=""):
        """Add Magnet URL
        Args:
            torrent_hash (str): The hash of the torrent "magnet:..."
            label        (str): Download kind (series, movies, books, ...)
        """
        data = {"action": "setprops", "hash": torrent_hash, "s": "label", "v": label}
        return self.get(data=data)


utorrent = uTorrentAPI()
