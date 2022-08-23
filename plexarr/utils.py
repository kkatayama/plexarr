import re
import json
from furl import furl

from nfl_data_py import import_team_desc, import_schedules
from datetime import datetime as dt
from pathlib import Path
import pandas as pd


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
