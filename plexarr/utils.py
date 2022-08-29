import xmltodict
import json
import re

from datetime import datetime as dt
from pathlib import Path
from furl import furl

from nfl_data_py import import_team_desc, import_schedules
import pandas as pd

import time
import socket
import select
from contextlib import contextmanager


# -- https://stackoverflow.com/a/41510011/3370913
def camel_case(s):
    RE_WORDS = re.compile(r'''
        # Find words in a string. Order matters!
        [A-Z]+(?=[A-Z][a-z]) |  # All upper case before a capitalized word
        [A-Z]?[a-z]+ |  # Capitalized words / all lower case
        [A-Z]+ |  # All upper case
        \d+  # Numbers
    ''', re.VERBOSE)
    words = RE_WORDS.findall(s)
    if words:
        return words.pop(0) + ''.join(l.capitalize() for l in words)
    return ''


def gen_xmltv_xml(channels=[], programs=[], url=''):
    """Template for generating XMLTV TV Guide!.

    Args:
        Required - channels (list) - List of channel objects
        Required - programs (list) - List of program objects
    Returns:
        XMLTV String
    Required Object Format:
        channel - {
            "tvg_id": tvg_id,
            "tvg_name": tvg_name,
            "tvg_logo": tvg_logo,
            "epg_desc": epg_desc,
        }
        program - {
            "tvg_id": tvg_id,
            "epg_title": epg_title,
            "epg_start": epg_start,
            "epg_stop": epg_stop,
            "epg_desc": epg_desc
        }
    """

    xml_header = f"""\
<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv generator-info-name="IPTV" generator-info-url="{furl(url).origin}">
"""

    xml_channels = ""
    for channel in channels:
        tvg_id, tvg_name, tvg_logo, epg_desc = channel.values()
        xml_channels += f"""\
    <channel id="{tvg_id}">
        <display-name>{tvg_name}</display-name>
        <icon src="{tvg_logo}"/>
    </channel>
"""

    xml_programs = ""
    for program in programs:
        if len(program.values()) == 5:
            tvg_id, epg_title, epg_start, epg_stop, epg_desc = program.values()
        else:
            tvg_id, epg_title, epg_start, epg_stop, epg_desc, epg_icon = program.values()
        xml_programs += f"""\
    <programme channel="{tvg_id}" start="{epg_start}" stop="{epg_stop}">'
        <title lang="en">{epg_title}</title>'
        <desc lang="en">{epg_desc}</desc>'
    </programme>'
"""

    xml_footer = """\
</tv>
"""

    xmltv = xml_header + xml_channels + xml_programs + xml_footer
    return xmltv


def m3u_to_json(src):
    temp = src.splitlines()
    temp_info = temp.pop(0)

    data = {}
    regex_info = r'#EXTM3U url-tvg="(?P<url_tvg>.*)" x-tvg-url="(?P<x_tvg_url>.*)"'
    info = re.search(regex_info, temp_info).groupdict()
    data.update(info)

    streams = []
    regex_stream = r"""
        [#]EXTINF:(?P<ext_inf>\d+)                          | # TODO
        channelID=["](?P<channelID>[^"]+)["]     | # Channel ID
        tvg-chno=["](?P<tvg_chno>[^"]+)["]       | # TVG Number
        tvg-name=["](?P<tvg_name>[^"]+)["]       | # TVG Name
        tvg-id=["](?P<tvg_id>[^"]+)["]           | # TVG ID
        tvg-logo=["](?P<tvg_logo>[^"]+)["]       | # TVG LOGO
        group-title=["](?P<group_title>[^"]+)["] | # Group Title
        ,(?P<chan_name>.*)                       | # Channel Name == TVG Name
        (?P<stream_url>(http://\d+.\d+.\d+.\d+\:\d+/stream/.*))
    """
    r_stream = re.compile(regex_stream, re.VERBOSE)
    for line in list(map("\n".join, zip(temp[0::2], temp[1::2]))):
        streams.append(
            {
                k: v
                for m in r_stream.finditer(line)
                for k, v in m.groupdict().items()
                if v
            }
        )
    data.update({"streams": streams})
    return json.dumps(data)

def epg_to_dict(src):
    # -- https://github.com/martinblech/xmltodict | https://github.com/dart-neitro/xmltodict3
    """
    <?xml version="1.0" encoding="utf-8"?>
    <tv>
        <generator-info-name>IPTV</generator-info-name>
        <channel id="fox8wghp.us">
                <display-name>USA FOX 8 WGHP HIGH POINT</display-name>
                <icon src="https://tse1.mm.bing.net/th?id=OIP.STWepjwC5f9QLqwGq-eRVAAAAA&amp;pid=Api&amp;rs=1&amp;c=1&amp;qlt=95&amp;w=85&amp;h=113"></icon>
        </channel>
        <programme start="20220218080000 +0000" stop="20220218103000 +0000" start_timestamp="1645171200" stop_timestamp="1645180200" channel="abckmiz.us">
                <title>ABC World News Now</title>
                <desc>This news broadcast presents the morning's top stories and breaking news from around the world.</desc>
        </programme>
    </tv>
    {
        'tv': {
            'generator-info-name': 'IPTV',
            'channel': [
                {'@id': 'fox8wghp.us', 'display-name': 'USA FOX 8 WGHP HIGH POINT', 'icon': {'@src': 'https://tse1.mm.bing.net/th?id=OIP.STWepjwC5f9QLqwGq-eRVAAAAA&pid=Api&rs=1&c=1&qlt=95&w=85&h=113'}},
            ],
            'programme': [
                {'@start': '20220218080000 +0000', '@stop': '20220218103000 +0000', '@start_timestamp': '1645171200', '@stop_timestamp': '1645180200', '@channel': 'abckmiz.us',
                    'title': 'ABC World News Now',
                    'desc': "This news broadcast presents the morning's top stories and breaking news from around the world."
                },
            ]
        }
    }
    """
    xml = Path(src).read_text() if Path(src).is_file() else src
    # return xmltodict.parse(xml, attr_prefix="", dict_constructor=dict)
    return xmltodict.parse(xml, dict_constructor=dict)

def dict_to_epg(src):
    """
    <?xml version="1.0" encoding="utf-8"?>
    <tv>
        <generator-info-name>IPTV</generator-info-name>
        <channel id="fox8wghp.us">
                <display-name>USA FOX 8 WGHP HIGH POINT</display-name>
                <icon src="https://tse1.mm.bing.net/th?id=OIP.STWepjwC5f9QLqwGq-eRVAAAAA&amp;pid=Api&amp;rs=1&amp;c=1&amp;qlt=95&amp;w=85&amp;h=113"></icon>
        </channel>
        <programme start="20220218080000 +0000" stop="20220218103000 +0000" start_timestamp="1645171200" stop_timestamp="1645180200" channel="abckmiz.us">
                <title>ABC World News Now</title>
                <desc>This news broadcast presents the morning's top stories and breaking news from around the world.</desc>
        </programme>
    </tv>
    {
        'tv': {
            'generator-info-name': 'IPTV',
            'channel': [
                {'@id': 'fox8wghp.us', 'display-name': 'USA FOX 8 WGHP HIGH POINT', 'icon': {'@src': 'https://tse1.mm.bing.net/th?id=OIP.STWepjwC5f9QLqwGq-eRVAAAAA&pid=Api&rs=1&c=1&qlt=95&w=85&h=113'}},
            ],
            'programme': [
                {'@start': '20220218080000 +0000', '@stop': '20220218103000 +0000', '@start_timestamp': '1645171200', '@stop_timestamp': '1645180200', '@channel': 'abckmiz.us',
                    'title': 'ABC World News Now',
                    'desc': "This news broadcast presents the morning's top stories and breaking news from around the world."
                },
            ]
        }
    }
    """
    return xmltodict.unparse(src, pretty=True)


def getNFLTeams():
    # -- get NFL season start year
    today = dt.now()
    year = (today.year - 1) if (today.month < 3) else today.year

    # -- read cached data if exists: plexarr/data/nfl_teams_2022.js
    js = Path(__file__).parent.joinpath(f'data/nfl_teams_{year}.js')
    if js.exists():
        with open(str(js)) as f:
            return json.load(f)
    else:
        # -- fetch NFL data
        df_schedule = import_schedules([year])
        df_teams = import_team_desc()
        df_week1 = df_schedule[(df_schedule["week"] == 1)]

        # -- index filters
        week1_home_teams = df_teams["team_abbr"].isin(df_week1["home_team"])
        week1_away_teams = df_teams["team_abbr"].isin(df_week1["away_team"])

        # -- merge + filter data
        df = df_teams[(week1_home_teams) | (week1_away_teams)]
        df = df[["team_name", "team_nick", "team_abbr", "team_conf", "team_division"]]
        df.reset_index(drop=True, inplace=True)

        # -- cache data
        df.to_json(str(js), orient='records', indent=2)

        # -- return List of Team Objects (records)
        return df.to_dict(orient="records")


# -- https://stackoverflow.com/a/54422402
def to_csv(df, path):
    # Prepend dtypes to the top of df
    df2 = df.copy()
    df2.loc[-1] = df2.dtypes
    df2.index = df2.index + 1
    df2.sort_index(inplace=True)
    # Then save it to a csv
    df2.to_csv(path, index=False)

def read_csv(path):
    # Read types first line of csv
    dtypes = {key: value for (key, value) in pd.read_csv(path,
              nrows=1).iloc[0].to_dict().items() if 'date' not in value}

    parse_dates = [key for (key, value) in pd.read_csv(path,
                   nrows=1).iloc[0].to_dict().items() if 'date' in value]
    # Read the rest of the lines with the types from above
    return pd.read_csv(path, dtype=dtypes, parse_dates=parse_dates, skiprows=[1]).fillna('')


# -- https://github.com/cherezov/dlnap/blob/08001ef6e1246215bc71bd2f4220b982dbb8b395/dlnap/dlnap.py#L375
@contextmanager
def _send_udp(to, packet):
    """Send UDP message to group
    to -- (host, port) group to send the packet to
    packet -- message to send
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.sendto(packet.encode(), to)
    yield sock
    sock.close()

def find_xteve_devices():
    """Find All xTeVe Devices"""
    payload = "\r\n".join(
        [
            "M-SEARCH * HTTP/1.1",
            "User-Agent: {}/{}".format(
                "Mozilla",
                "5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0",
            ),
            "HOST: {}:{}".format("239.255.255.250", 1900),
            "Accept: */*",
            'MAN: "ssdp:discover"',
            "ST: {}".format("ssdp:all"),
            "MX: {}".format(3),
            "",
            "",
        ]
    )
    timeout = 1
    devices = []
    with _send_udp(("239.255.255.250", 1900), payload) as sock:
        start = time.time()
        while True:
            if time.time() - start > timeout:
                break
            r, w, x = select.select([sock], [], [sock], 1)
            if sock in r:
                data, addr = sock.recvfrom(1024)
                if b"xteve" in data:
                    m = re.search(rb"(LOCATION:\s+)(?P<location>.*)(\r\n)", data)
                    ip = addr[0]
                    location = furl(m.groupdict()["location"].decode())
                    m3u = location.join('/m3u/xteve.m3u')
                    epg = location.join('/xmltv/xteve.xml')
                    devices.append({
                        'ip': ip,
                        'location': location.url,
                        'm3u': m3u.url,
                        'epg': epg.url,
                    })
    return devices
