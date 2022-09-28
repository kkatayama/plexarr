#!/usr/bin/env python3
from gevent import monkey; monkey.patch_all()

import mock  # unittest.mock in Python 3.3+
with mock.patch('gevent.monkey.patch_all', lambda *args, **kwargs: None):
    from plexarr.xtream_api import XtreamAPI
import time


def getLemo():
    xtream = XtreamAPI()
    return xtream.getM3U(iptv="lemo")

def getLemo2():
    xtream = XtreamAPI()
    return xtream.getM3U(iptv="lemo2")


print(getLemo())
#time.sleep(10)
print(getLemo2())
