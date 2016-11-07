import base64
import json
import re
from enum import IntEnum, unique
from threading import Timer
import pickle
import os
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from pyee import EventEmitter
import SteamID

# set up logging
from utils import logger

from utils import CommunityURL, APIUrl, generateSessionID, urlForAvatarHash
from utils import dictDiff

# enums in other modules
from chat import ChatState, PersonaState, PersonaStateFlag
from profile import PrivacyState, CommentPrivacyState


@unique
class LoginStatus(IntEnum):
    Waiting, LoginFailed, LoginSuccessful, SteamGuard, TwoFactor, Captcha = range(
        6)


@unique
class LoggedIn(IntEnum):
    GeneralError = 0
    LoggedIn = 1
    FamilyView = 2


class SteamAPI(object):
    '''
    Provides a Python interface to the Steam Web API, for chat
    '''

    from chat import _initialLoadFriends, _chatPoll, _loadFriendList, _chatUpdatePersona
    from chat import chatLogon, chatMessage, chatLogoff

    from profile import setupProfile, editProfile, profileSettings, uploadAvatar
    from market import getMarketApps

    def __init__(self):
        self.oauth_client_id = "DE45CD61"
        self.session = requests.Session()
        self._captchaGid = -1
        self.chatState = ChatState.Offline
        self.event = EventEmitter()

        self.session.cookies.set("Steam_Language", "english")
        self.session.cookies.set("timezoneOffset", "0,0")
        self.session.cookies.set("mobileClientVersion", "0 (2.1.3)")
        self.session.cookies.set("mobileClient", "android")

        self.jarLoaded = False

        self._timers = []
        self._cache = {}

        self.chatFriends = {}

        self._mobileHeaders = {
            "X-Requested-With": "com.valvesoftware.android.steam.community",
            "referer": "https://steamcommunity.com/mobilelogin?oauth_client_id=DE45CD61&oauth_scope=read_profile%20write_profile%20read_client%20write_client",
            "user-agent": "Mozilla/5.0 (Linux; U; Android 4.1.1; en-us; Google Nexus 4 - 4.1.1 - API 16 - 768x1280 Build/JRO03S) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
            "accept": "text/javascript, text/html, application/xml, text/xml, */*"
        }

    def save_cookies(self, filename):
        '''
        Dumps cookies to a file
        '''
        with open(filename, 'w') as f:
            f.truncate()
            pickle.dump(self.session.cookies._cookies, f)

    def load_cookies(self, filename):
        '''
        Loads cookies from a previous cookie dump
        '''
        if not os.path.isfile(filename):
            return False

        with open(filename) as f:
            cookies = pickle.load(f)
            if cookies:
                jar = requests.cookies.RequestsCookieJar()
                jar._cookies = cookies
                self.session.cookies = jar
            else:
                return False

        return True

    def emit(self, event, *data):
        self.event.emit(event, *data)

    def timer(self, interval, func, args=()):
        timer = Timer(interval, func, args)
        timer.daemon = True
        timer.start()

    def _checkHttpError(self, response):
        '''
        Checks for Steam's definition of an error
        '''
        if response.status_code >= 300 and response.status_code <= 399 and "/login" in response.headers["location"]:
            self.emit('sessionExpired', response.status_code)
            return True

        if response.status_code >= 400:
            response.raise_for_status()
            return True

        return False

    def login(self, cookie_file=None, **details):
        '''
        Initiates login for Steam Web chat.
        '''
        if cookie_file:
            self.load_cookies(cookie_file)

        rsakey = self.session.post(CommunityURL("login", "getrsakey"), data={
            "username": details["username"]}, headers=self._mobileHeaders)

        if rsakey.status_code != requests.codes.ok:
            rsakey.raise_for_status()
            return None, None

        rsakey = rsakey.json()

        mod = long(rsakey["publickey_mod"], 16)
        exp = long(rsakey["publickey_exp"], 16)
        rsa_key = RSA.construct((mod, exp))
        rsa = PKCS1_v1_5.PKCS115_Cipher(rsa_key)

        form = {
            "captcha_text": details.get("captcha", ""),
            "captchagid": self._captchaGid,
            "emailauth": details.get('steamguard', ""),
            "emailsteamid": "",
            "password": base64.b64encode(rsa.encrypt(details["password"])),
            "remember_login": "true",
            "rsatimestamp": rsakey["timestamp"],
            "twofactorcode": details.get('twofactor', ""),
            "username": details['username'],
            "oauth_client_id": "DE45CD61",
            "oauth_scope": "read_profile write_profile read_client write_client",
            "loginfriendlyname": "#login_emailauth_friendlyname_mobile"
        }

        dologin = self.session.post(
            CommunityURL("login", "dologin"), data=form, headers=self._mobileHeaders).json()

        self._cache = details
        if not dologin["success"] and dologin.get("emailauth_needed"):
            return LoginStatus.SteamGuard
        elif not dologin["success"] and dologin.get("requires_twofactor"):
            return LoginStatus.TwoFactor
        elif not dologin["success"] and dologin.get("captcha_needed"):
            print "Captcha URL: https://steamcommunity.com/public/captcha.php?gid=" + dologin["captcha_gid"]
            self._captchaGid = dologin["captcha_gid"]
            return LoginStatus.Captcha
        elif not dologin["success"]:
            raise Exception(dologin.get("message", "Unknown error"))
        else:
            sessionID = generateSessionID()
            oAuth = json.loads(dologin["oauth"])
            self.session.cookies.set("sessionid", str(sessionID))
            self.sessionID = str(sessionID)

            self.steamID = SteamID.SteamID(oAuth["steamid"])
            self.oAuthToken = oAuth["oauth_token"]

            self._cache = {}
            self.steamguard = str(self.steamID) + "||" + \
                self.session.cookies.get(
                    "steamMachineAuth" + str(self.steamID), '')

            if cookie_file:
                self.save_cookies(cookie_file)

            return LoginStatus.LoginSuccessful

        self._cache = details
        return LoginStatus.LoginFailed

    def retry(self, **details):
        '''
        Retries a previously failed login attempt.
        Commonly used to submit a SteamGuard or Mobile Authenticator code.
        '''
        deets = self._cache.copy()
        deets.update(details)
        return self.login(**deets)

    def oAuthLogin(self, steamguard, token):
        '''
        Allows password-less login via the following attributes set by SteamAPI.login:
            Instance.steamguard
            Instance.oAuthToken
        '''
        steamguard = steamguard.split('||')
        steamID = SteamID.SteamID(steamguard[0])

        form = {"access_token": token}
        login = self.session.post(
            APIUrl("IMobileAuthService", "GetWGToken"), data=form)

        resp = login.json().get('response', {})
        if not login or 'token' not in resp or 'token_secure' not in resp:
            logger.error("Error logging in with OAuth: Malformed response")
            return LoginStatus.LoginFailed

        sid = str(steamID.SteamID64)
        self.session.cookies.set('steamLogin', sid + '||' + resp['token'])
        self.session.cookies.set(
            'steamLoginSecure', sid + '||' + resp['token_secure'])
        if steamguard[1]:
            self.session.cookies.set('steamMachineAuth' + sid, steamguard[1])
        self.session.cookies.set(
            'sessionid', self.session.cookies.get('sessionid', generateSessionID()))

        return LoginStatus.LoginSuccessful

    def parentalUnlock(self, pin):
        unlock = self.session.post(
            CommunityURL('parental', 'ajaxunlock'), data={"pin": pin})

        if not unlock:
            logger.error("Error unlocking parental with pin: Unknown error")
            return

        if unlock.status_code != 200:
            logger.error('HTTP error %s', resp.status_code)
            return

        resp = unlock.json()
        if not resp:
            logger.error("Error unlocking parental with pin: Invalid response")
            return False

        if not resp.get('success'):
            logger.error("Error unlocking parental with pin: Incorrect PIN")
            return False

        return True

    def getNotifications(self):
        notifications = self.session.get(
            CommunityURL('actions', 'GetNotificationCounts'))

        if not notifications:
            logger.error("Error retrieving notifications")

        resp = notifications.json()

        items = {
            "comments": 4,
            "items": 5,
            "invites": 6,
            "gifts": 8,
            "chat": 9,
            "trades": 1
        }

        notifs = {}

        for item, key in items.iteritems():
            notifs[item] = resp['notifications'][str(key)]

        return notifs

    def resetItemNotifications(self):
        self.session.get(CommunityURL('my', 'inventory'))
        return True

    @property
    def loggedIn(self):
        resp = self.session.get(CommunityURL('my', ''), allow_redirects=False)

        if resp.status_code != 302 and resp.status_code != 403:
            logger.error('HTTP error %s', resp.status_code)
            return LoggedIn.GeneralError

        if resp.status_code == 403:
            return LoggedIn.FamilyView

        id_match = re.compile(
            r'steamcommunity\.com(\/(id|profiles)\/[^\/]+)\/?')

        if id_match.search(resp.headers['location']):
            return LoggedIn.LoggedIn

        return LoggedIn.GeneralError

    def getWebApiOauthToken(self):
        '''
        Retrives necessary OAuth token for Steam Web chat
        '''
        resp = self.session.get("https://steamcommunity.com/chat")
        if self._checkHttpError(resp):
            return ("HTTP Error", None)

        token = re.compile(ur'"([0-9a-f]{32})"')
        matches = token.search(resp.text)
        if matches:
            self._initialLoadFriends(resp.text)
            return (None, matches.group().replace('"', ''))

        return ("Malformed Response", None)
