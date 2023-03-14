import xmltodict
import json
import re

from datetime import datetime as dt
from pathlib import Path
from furl import furl
import urllib.request
import requests
import inspect

from nfl_data_py import import_team_desc, import_schedules
import pandas as pd

from contextlib import contextmanager
from ipaddress import ip_address
import time
import socket
import select

import m3u8
from m3u8 import protocol
from m3u8.parser import save_segment_custom_value

from logging.handlers import TimedRotatingFileHandler
from logging import StreamHandler
from coloredlogs import ColoredFormatter, find_program_name, ProgramNameFilter
import coloredlogs
import logging
import sys
import os

from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn


def get_py_path(verbose=False):
    # return Path(globals()['_dh'][0]) if globals().get('_dh') else Path(__file__)
    print('starting at currentframe().f_back') if verbose else ''
    env = inspect.currentframe().f_back.f_locals
    if ((not env.get('_dh')) and (not env.get('__file__'))):
        print('going deeper: currentframe().f_back.f_back') if verbose else ''
        env = inspect.currentframe().f_back.f_back.f_locals
        if ((not env.get('_dh')) and (not env.get('__file__'))):
            print('even deeper: currentframe().f_back.f_back.f_back') if verbose else ''
            env = inspect.currentframe().f_back.f_back.f_back.f_locals
    if env.get('_dh'):
        print('==ipython shell==') if verbose else ''
        if env.get('__file__'):
            return Path(env["_dh"][0], env["__file__"]).resolve().parent

        if verbose:
            print('<File.py>: NOT FOUND!')
            print('Next time run with:\n  ipython -i -- <File.py>')
            print('using cwd()')
        return Path(env["_dh"][0])

    print(f'env = {env}') if verbose else ''
    return Path(env["__file__"]).resolve().parent


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
    # -- cleanup excess new-lines
    src = re.sub(r'\n+', '\n', src.strip())
    temp = src.splitlines()
    temp_info = temp.pop(0)

    # -- handle lemo xui m3u with extra line of info
    extra_info = []
    for i, tmp in enumerate(temp):
        if not tmp.startswith(('#EXTINF', 'http')):
            extra_info.append(tmp)
        else:
            break
    temp = temp[i:]

    data = {}
    regex_info = r"""
        #EXTM3U url-tvg="(?P<url_tvg>.*)" x-tvg-url="(?P<x_tvg_url>.*)"   |
        #EXTM3U(.*)
    """
    info = re.search(regex_info, temp_info, re.VERBOSE).groupdict()
    data.update(info)

    streams = []
    regex_stream = r"""
        [#]EXTINF:(?P<ext_inf>(\d|-)+)                          | # TODO
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


def m3u_to_dict(src):
    def parse_iptv_attributes(line, lineno, data, state):
        # Customize parsing #EXTINF
        if line.startswith(protocol.extinf):
            title = ''
            chunks = line.replace(protocol.extinf + ':', '').split(',', 1)
            if len(chunks) == 2:
                duration_and_props, title = chunks
            elif len(chunks) == 1:
                duration_and_props = chunks[0]

            additional_props = {}
            chunks = duration_and_props.strip().split(' ', 1)
            if len(chunks) == 2:
                duration, raw_props = chunks
                matched_props = re.finditer(r'([\w\-]+)="([^"]*)"', raw_props)
                for match in matched_props:
                    additional_props[match.group(1)] = match.group(2)
            else:
                duration = duration_and_props

            if 'segment' not in state:
                state['segment'] = {}
            state['segment']['duration'] = float(duration)
            state['segment']['title'] = title

            # Helper function for saving custom values
            save_segment_custom_value(state, 'extinf_props', additional_props)

            # Tell 'main parser' that we expect an URL on next lines
            state['expect_segment'] = True

            # Tell 'main parser' that it can go to next line, we've parsed current fully.
            return True
    def getStreamID(url):
        path = Path(str(furl(url).path))
        path = Path(str(path).removesuffix(''.join(path.suffixes)))
        stream_id = path.name
        return stream_id

    parsed = m3u8.load(src, custom_tags_parser=parse_iptv_attributes)
    m3u = [dict(s.custom_parser_values['extinf_props'], **{"url": s.uri, "title": s.title,
                   "stream_id": getStreamID(s.uri), "duration": int(s.duration)})
           for s in parsed.segments]
    return m3u

def dict_to_m3u(src):
    m3u = ['#EXTM3U']
    for s in src:
        m3u += [f'#EXTINF:{s.get("duration")} tvg-id="{s.get("tvg-id")}" tvg-name="{s.get("tvg-name")} tvg-logo="{s.get("tvg-logo")}" group-title="{s.get("group-title")}",{s.get("title")}']
        m3u += [f'{s.get("url")}']
    return '\n'.join(m3u)

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

    if len(src) > 100:
        xml = src
    else:
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
# -- https://www.electricmonk.nl/log/2016/07/05/exploring-upnp-with-python/
def find_xteve_devices(ip_only=False, domain_only=False):
    """Find All xTeVe Devices"""
    payload = "\r\n".join([
        "M-SEARCH * HTTP/1.1", "HOST: 239.255.255.250:1900",
        'MAN: "ssdp:discover"',"ST: ssdp:all",
        "MX: 3", "", "",
    ])
    devices = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.settimeout(1)
        sock.sendto(payload.encode(), ("239.255.255.250", 1900))
        try:
            while True:
                resp, (addr, port) = sock.recvfrom(1024)
                data = resp.decode()
                if "xteve" in data:
                    loc = furl(*re.search(r"LOCATION:\s+(.*)\r\n", data).groups())
                    try:
                        ip_address(loc.host)
                        location = loc;
                        is_ip = True
                        is_domain = False
                    except ValueError:
                        is_ip = False
                        is_domain = True
                        try:
                            base_url = urllib.request.urlopen(f'{loc.scheme}://{loc.host}').geturl()
                        except Exception:
                            base_url = urllib.request.urlopen(f'{loc.scheme}://{loc.host}:{loc.port}').geturl()
                        location = furl(base_url).join(loc.path)

                    if (ip_only and is_ip) or (domain_only and is_domain) or (not ip_only and not domain_only):
                        devices.append({
                            'ip': addr, 'port': port,
                            'location': location.url,
                            'm3u': location.join('/m3u/xteve.m3u').url,
                            'epg': location.join('/xmltv/xteve.xml').url,
                        })

        except socket.timeout:
            pass
    return pd.DataFrame(devices).drop_duplicates().to_dict('records')


def convertEPGTime(p_time="", dt_obj=False, epg_fmt=False):
    """Convert EPG Programme "start" and/or "stop" time from UTC to EST

    Note:
        Do not enable `dt_obj` and `epg_fmt` at the same time.
        Setting `dt_obj` takes precedence over `epg_fmt`.

    Args:
        p_time (str, datetime): The datetime string (or object) to convert
        dt_obj (:obj:`bool`, optional): Request datetime object. Default=False
        epg_fmt (bool, optional): Request epg formatted string. Default=False

    Returns:
        Converted EST time as a datetime or str object

    Examples:
        >>> convertEPGTime("20210803180000 +0000")
        '2021-08-03 02:00:00 PM'

        >>> convertEPGTime("20210803180000 +0000", epg_fmt=True)
        '20210803140000 -0400'

        >>> convertEPGTime("20210803180000 +0000", dt_obj=True)
        Timestamp('2021-08-03 14:00:00-0400', tz='US/Eastern')

    """
    est_dt = pd.to_datetime(p_time).tz_convert('US/Eastern')
    if dt_obj:
        return est_dt
    if epg_fmt:
        return est_dt.strftime("%Y%m%d%H%M%S %z")
    return est_dt.strftime("%Y-%m-%d %I:%M:%S %p")


def getEPGTimeNow(dt_obj=False, epg_fmt=False):
    """Return EPG Programme "start" and/or "stop" time based on current time (30 minute start)

    Args:
        dt_obj (:obj:`bool`, optional): Request datetime object. Default=False
        epg_fmt (bool, optional): Request epg formatted string. Default=False

    Returns:
        The current time as a datetime or str object

    Examples:
    >>> getEPGTimeNow()
    '2021-08-03 04:00:00 PM'

    >>> getEPGTimeNow(epg_fmt=True)
    '20210803160000 -0400'

    >>> getEPGTimeNow(dt_obj=True)
    Timestamp('2021-08-03 16:00:00-0400', tz='US/Eastern')
    """
    est_dt = pd.to_datetime(time.time(), unit='s', utc=True).tz_convert('US/Eastern').floor('30min')
    if dt_obj:
        return est_dt
    if epg_fmt:
        return est_dt.strftime("%Y%m%d%H%M%S %z")
    return est_dt.strftime("%Y-%m-%d %I:%M:%S %p")


def find_cmd(cmd, find_all=False):
    cmds = []
    for cmd_path in filter(os.path.isdir, os.environ['PATH'].split(':')):
        if cmd.lower() in map(str.lower, os.listdir(cmd_path)):
            index = list(map(str.lower, os.listdir(cmd_path))).index(cmd.lower())
            bin_cmd = os.path.join(cmd_path, os.listdir(cmd_path)[index])
            if find_all:
                cmds += [bin_cmd]
            else:
                return bin_cmd
    return cmds


# -- taken from: "https://github.com/apsun/AniConvert/blob/master/aniconvert.py"
def process_handbrake_output(process):
    def print_err(message="", end="\n", flush=False):
        print(message, end=end, file=sys.stderr)
        if flush:
            sys.stderr.flush()

    pattern1 = re.compile(r"Encoding: task \d+ of \d+, (\d+\.\d\d) %")
    pattern2 = re.compile(
        r"Encoding: task \d+ of \d+, (\d+\.\d\d) % "
        r"\((\d+\.\d\d) fps, avg (\d+\.\d\d) fps, ETA (\d\dh\d\dm\d\ds)\)")
    percent_complete = None
    current_fps = None
    average_fps = None
    estimated_time = None
    prev_message = ""
    format_str = "Progress: {percent:.2f}% done"
    long_format_str = format_str + " (FPS: {fps:.2f}, average FPS: {avg_fps:.2f}, ETA: {eta})"
    try:
        while True:
            output = process.stdout.readline()
            if len(output) == 0:
                break
            output = output.rstrip()
            match = pattern1.match(output)
            if not match:
                continue
            percent_complete = float(match.group(1))
            match = pattern2.match(output)
            if match:
                format_str = long_format_str
                current_fps = float(match.group(2))
                average_fps = float(match.group(3))
                estimated_time = match.group(4)
            message = format_str.format(
                percent=percent_complete,
                fps=current_fps,
                avg_fps=average_fps,
                eta=estimated_time)
            print_err(message, end="")
            blank_count = max(len(prev_message) - len(message), 0)
            print_err(" " * blank_count, end="\r")
            prev_message = message
    finally:
        print_err(flush=True)


def downloadFile(url='', params={}, file_name='', file_path=''):
    # -- Get File Path -- #
    if not file_path:
        file_path = Path(get_py_path(), 'downloads')
        file_path.mkdir(exist_ok=True)

    # -- Get File Name -- #
    if not file_name:
        r = requests.get(url, params=params)
        file_name = Path(furl(r.url).pathstr).name

    full_path = str(Path(file_path, file_name))

    # -- Progress Bar Column Parameters -- #
    text_column  = TextColumn("[bold blue]{task.fields[file_name]}", justify="right")
    bar_column   = BarColumn(bar_width=None)
    work_column  = TextColumn("[progress.percentage]{task.percentage:>3.1f}%")
    dot          = TextColumn("•")
    down_column  = DownloadColumn()
    speed_column = TransferSpeedColumn()
    time_column  = TimeRemainingColumn()

    # -- Downloading with Progress Bar -- #
    try:
        with Progress(text_column, bar_column, work_column, dot, down_column, dot, speed_column, dot, time_column) as progress:
            progress.console.log(f"Requesting {url}")
            r = requests.get(url, params=params, stream=True)
            total = int(r.headers.get('content-length', 0))
            with open(full_path, "wb") as f:
                if total:
                    task = progress.add_task("download", file_name=file_name, total=total)
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))
                else:
                    f.write(r.content)
        progress.console.log(f"Downloaded: {str(file_path)}")
    except KeyboardInterrupt:
        sys.exit(1)

    return full_path


# -- LOGGER CONFIGS -- #
MODULE = coloredlogs.find_program_name()
LOG_FILE = 'logs/{}.log'.format(os.path.splitext(MODULE)[0])
field_styles = {
    'asctime': {'color': 221, 'bright': True},
    'programname': {'color': 45, 'faint': True},
    'funcName': {'color': 177, 'normal': True},
    'lineno': {'color': 'cyan', 'bright': True}
}
level_styles = {
    "debug": {'color': 'green', 'bright': True},
    "info": {'color': 'white', 'bright': True},
    "warning": {'color': "yellow", 'normal': True},
    "error": {'color': "red", 'bright': True},
    "critical": {'color': 'red', 'bold': True, 'background': 'red'}
}
log_format = "[%(asctime)s] [%(levelname)-8s] [%(programname)s: %(funcName)s();%(lineno)s] %(message)s"


def getFileHandler():
    log_file_formatter = coloredlogs.ColoredFormatter(log_format, field_styles=field_styles, level_styles=level_styles)
    log_file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
    log_file_handler.addFilter(coloredlogs.ProgramNameFilter())
    log_file_handler.setFormatter(log_file_formatter)
    return log_file_handler


def getLogger(level='DEBUG', suppressLibLogs=False):
    # -- create log directory if needed -- #
    Path(LOG_FILE).parent.mkdir(exist_ok=True)

    # -- CREATE LOGGER -- #
    logger = logging.getLogger(MODULE)
    logger.setLevel(eval(f'logging.{level}'))
    logger.addHandler(getFileHandler())
    if suppressLibLogs:
        # -- hide log messages from imported libraries
        coloredlogs.install(level=level, fmt=log_format, field_styles=field_styles, level_styles=level_styles, logger=logger)
    else:
        coloredlogs.install(level=level, fmt=log_format, field_styles=field_styles, level_styles=level_styles)
    return logger



class Logger(object):
    """
    Custom Wrapper for ColoredLogs

    Usage:
        from plexarr.utils import Logger

        log = Logger(log_console=True).createLogger()
        log.debug('TEST DEBUG')
    """
    def __init__(self, level='DEBUG', log_file=True, log_console=False):
        """
        Setup for logger

        Args:
            Optional - level (str|int)      - set logging level for both log file and console output
            Optional - log_file (bool)      - save logging output to log file
            Optional - log_console (bool)   - display logging output to console
        """
        # -- LOGGER CONFIGS -- #
        self.level = level
        self.log_file = log_file
        self.log_console = log_console
        self.MODULE = find_program_name()
        self.LOG_PATH = 'logs/{}.log'.format(os.path.splitext(self.MODULE)[0])
        self.field_styles = {
            'asctime': {'color': 221, 'bright': True},
            'programname': {'color': 45, 'faint': True},
            'funcName': {'color': 177, 'normal': True},
            'lineno': {'color': 'cyan', 'bright': True}
        }
        self.level_styles = {
            "debug": {'color': 'green', 'bright': True},
            "info": {'color': 'white', 'bright': True},
            "warning": {'color': "yellow", 'normal': True},
            "error": {'color': "red", 'bright': True},
            "critical": {'color': 'red', 'bold': True, 'background': 'red'}
        }
        self.log_format = "[%(asctime)s] [%(levelname)-8s] [%(programname)s: %(funcName)s();%(lineno)s] %(message)s"

    def createLogger(self):
        logger = logging.getLogger(self.MODULE)
        logger.setLevel(eval(f'logging.{self.level}'))

        if self.log_file:
            # -- create log directory if needed -- #
            Path(self.LOG_PATH).parent.mkdir(exist_ok=True)
            logger.addHandler(self.getFileHandler())

        if self.log_console:
            logger.addHandler(self.getConsoleHandler())

        #coloredlogs.install(level=logging.DEBUG, fmt=log_format, field_styles=field_styles, level_styles=level_styles, logger=logger)
        return logger

    def getFileHandler(self):
        log_file_formatter = ColoredFormatter(self.log_format, field_styles=self.field_styles, level_styles=self.level_styles)
        log_file_handler = TimedRotatingFileHandler(self.LOG_PATH, when='midnight')
        log_file_handler.setLevel(eval(f'logging.{self.level}'))
        log_file_handler.addFilter(ProgramNameFilter())
        log_file_handler.setFormatter(log_file_formatter)
        return log_file_handler

    def getConsoleHandler(self):
        console_formatter = ColoredFormatter(self.log_format, field_styles=self.field_styles, level_styles=self.level_styles)
        console_handler = StreamHandler(sys.stdout)
        console_handler.setLevel(eval(f'logging.{self.level}'))
        console_handler.addFilter(ProgramNameFilter())
        console_handler.setFormatter(console_formatter)
        return console_handler

# log = Logger(log_console=True).createLogger()
