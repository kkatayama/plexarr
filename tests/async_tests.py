# coding: utf-8
import nest_asyncio
nest_asyncio.apply()

from rich import print
import requests
import asyncio
import time


m3u_items = ["#EXTM3U\n"]

def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)
    return wrapped

@background
def getStreams(payload):
    api_url = 'http://star.iptvpanel.xyz/player_api.php'
    r = requests.get(api_url, params=payload)
    streams = r.json()
    print(f'getStreams() finished for "category_i =: {payload["category_id"]}": fetched {len(streams)} streams')
    return streams

def getCategories():
    """
    [
        {'category_id': '330', 'category_name': 'US | ENTERTAINTMENT', 'parent_id': 0}, 
        {'category_id': '332', 'category_name': 'US | SPORTS', 'parent_id': 0}, 
        {'category_id': '336', 'category_name': 'US | FOX', 'parent_id': 0}
    ]
    """
    groups = {'US | ENTERTAINTMENT', 'US | FOX', 'US | SPORTS'}
    api_url = 'http://star.iptvpanel.xyz/player_api.php'
    payload = {'username': '83MRPffhy5', 'password': '85SNBP2TWq', 'action': 'get_live_categories'}
    r = requests.get(url=api_url, params=payload)
    return list(filter(lambda x: x["category_name"] in groups, r.json()))
    
def getPaylods():
    """
    [
        {'username': '83MRPffhy5', 'password': '85SNBP2TWq', 'action': 'get_live_streams', 'category_id': '330'},
        {'username': '83MRPffhy5', 'password': '85SNBP2TWq', 'action': 'get_live_streams', 'category_id': '332'},
        {'username': '83MRPffhy5', 'password': '85SNBP2TWq', 'action': 'get_live_streams', 'category_id': '336'}
    ]
    """
    print('This runs Before Loop!')
    cats = getCategories()
    api_url = 'http://star.iptvpanel.xyz/player_api.php'
    payload = {'username': '83MRPffhy5', 'password': '85SNBP2TWq', 'action': 'get_live_streams'}
    return [dict(**payload, **{"category_id": c["category_id"]}) for c in cats]        


def code_to_run_after():
    print('This runs After Loop!')

start_time = time.perf_counter()

payloads = getPaylods()

loop = asyncio.get_event_loop() 
looper = asyncio.gather(*[getStreams(payload) for payload in payloads])
streams2 = loop.run_until_complete(looper) 

stop_time = time.perf_counter()


print(f'completed in {stop_time - start_time:0.4f} seconds')
