<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv generator-info-name="IPTV" generator-info-url="{{url}}">
% for channel in channels:
    <channel id="{{channel['tvg_id']}}">
        <display-name>{{channel['tvg_name']}}</display-name>
        <icon src="{{channel['tvg_logo']}}"/>
    </channel>
% end
% for program in programs:
    <programme channel="{{program['tvg_id']}}" start="{{program['epg_start']}}" stop="{{program['epg_stop']}}">
        <title lang="en">{{program['epg_title']}}</title>
        <desc lang="en">{{program['epg_desc']}}</desc>
    % if program.get('epg_icon'):
        <icon src="{{program['epg_icon']}}"/>
    % end
    </programme>
% end
</tv>
