import re


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


def gen_xmltv_xml(channels=[], programs=[]):
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

    xml_header = """\
<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv generator-info-name="IPTV" generator-info-url="http://jlwmedia.xyz:25461/">
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
        tvg_id, epg_title, epg_start, epg_stop, epg_desc = program.values()
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
