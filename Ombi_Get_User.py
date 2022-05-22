# coding: utf-8
from difflib import SequenceMatcher
from rich.console import escape
from functools import reduce
from plexarr import OmbiAPI
from rich import print


def similar(a, b):
    p = SequenceMatcher(None, a, b).ratio()
    if p > 0.85:
        return True
    return False


if __name__ == "__main__":
    ombi = OmbiAPI()
    username = "DizzyMissLizzy"
    users = [u["username"] for u in ombi.getUsers()]
    user = next(
        (filter(lambda u: similar(u["username"], username), ombi.getUsers())), None
    )
    print(user)
