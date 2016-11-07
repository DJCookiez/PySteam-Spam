from . import *
from pyquery import PyQuery as pq


def getMarketApps(self):
    resp = self.session.get('https://steamcommunity.com/market/')

    if resp.status_code != 200:
        logger.error('HTTP error %s', resp.status_code)
        return

    doc = pq(resp.text)
    apps = {}

    if doc('.market_search_game_button_group'):
        buttons = doc('.market_search_game_button_group > a')
        for button in buttons:
            appid = button.attrib["href"].split('appid=')[-1]
            apps[appid] = button.text_content().strip()

        return apps

    logger.error('Malformed response')
    return None
