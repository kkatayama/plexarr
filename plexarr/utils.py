import re
import json
from furl import furl


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
