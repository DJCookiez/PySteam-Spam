import re
import json
import SteamID
from enum import IntEnum, unique
from . import *


@unique
class ChatState(IntEnum):
    Offline, LoggingOn, LogOnFailed, LoggedOn = range(4)


@unique
class PersonaState(IntEnum):
    Offline = 0
    Online = 1
    Busy = 2
    Away = 3
    Snooze = 4
    LookingToTrade = 5
    LookingToPlay = 6
    Max = 7


@unique
class PersonaStateFlag(IntEnum):
    Default = 0
    HasRichPresence = 1
    InJoinableGame = 2

    OnlineUsingWeb = 256
    OnlineUsingMobile = 512
    OnlineUsingBigPicture = 1024


def _initialLoadFriends(self, resp):
    '''
    Parses the chat page for the initial friends state
    '''
    friends_json = re.compile(ur', (\[.*\]), ')
    matches = friends_json.search(resp)

    if matches:
        res = json.loads(
            matches.groups()[0])
        for friend in res:
            persona = {
                "steamID": SteamID.SteamID(friend['m_ulSteamID']),
                "personaName": friend['m_strName'],
                "personaState": PersonaState(friend['m_ePersonaState']),
                "personaStateFlags": PersonaStateFlag(friend.get('m_nPersonaStateFlags') or 0),
                "avatarHash": friend['m_strAvatarHash'],
                "inGame": friend.get('m_bInGame', False),
                "inGameAppID": friend.get('m_nInGameAppID', None),
                "inGameName": friend.get('m_strInGameName', None)
            }
            self.chatFriends[str(persona["steamID"])] = persona
            self.emit('initial', self.chatFriends)


def chatLogon(self, interval=500, uiMode="web", cookie_file=None):
    '''
    Logs into Web chat
    '''
    if cookie_file:
        self.load_cookies(cookie_file)

    if self.chatState == ChatState.LoggingOn or self.chatState == ChatState.LoggedOn:
        return

    logger.info("Requesting chat WebAPI token")
    self.chatState = ChatState.LoggingOn

    err, token = self.getWebApiOauthToken()
    if err:
        logger.error("Cannot get oauth token: %s", err)
        self.chatState = ChatState.LogOnFailed
        self.timer(5.0, self.chatLogon)
        return ChatState.LogOnFailed

    login = self.session.post(
        APIUrl("ISteamWebUserPresenceOAuth", "Logon"), data={"ui_mode": uiMode, "access_token": token})

    if login.status_code != 200:
        logger.error("Error logging into webchat (%s)", login.status_code)
        self.timer(5.0, self.chatLogon)
        return ChatState.LogOnFailed

    login_data = login.json()

    if login_data["error"] != "OK":
        logger.error("Error logging into webchat: %s", login_data["error"])
        self.timer(5.0, self.chatLogon)
        return ChatState.LogOnFailed

    self._chat = {
        "umqid": login_data["umqid"],
        "message": login_data["message"],
        "accessToken": token,
        "interval": interval
    }

    if cookie_file:
        self.save_cookies(cookie_file)

    self.chatState = ChatState.LoggedOn
    self._chatPoll()
    return ChatState.LoggedOn


def chatMessage(self, recipient, text, type_="saytext"):
    '''
    Sends a message to a specified recipient
    '''
    if self.chatState != ChatState.LoggedOn:
        raise Exception(
            "Chat must be logged on before messages can be sent")

    if not isinstance(recipient, SteamID.SteamID):
        recipient = SteamID.SteamID(recipient)

    form = {
        "access_token": self._chat["accessToken"],
        "steamid_dst": recipient.SteamID64,
        "text": text,
        "type": type_,
        "umqid": self._chat["umqid"]
    }

    self.session.post(
        APIUrl("ISteamWebUserPresenceOAuth", "Message"), data=form)


def chatLogoff(self):
    '''
    Requests a Logoff from Steam
    '''
    logoff = self.session.post(APIUrl("ISteamWebUserPresenceOAuth", "Logoff"), data={
        "access_token": self._chat["accessToken"],
        "umqid": self._chat["umqid"]
    })

    if logoff.status_code != 200:
        logger.error("Error logging off of chat: %s", logoff.status_code)
        self.timer(1.0, self.chatLogoff)
    else:
        self._chat = {}
        self.chatFriends = {}
        self.chatState = ChatState.Offline


def _chatPoll(self):
    '''
    Polls the Steam Web chat API for new events
    '''
    form = {
        "umqid": self._chat["umqid"],
        "message": self._chat["message"],
        "pollid": 1,
        "sectimeout": 20,
        "secidletime": 0,
        "use_accountids": 1,
        "access_token": self._chat["accessToken"]
    }

    response = self.session.post(
        APIUrl("ISteamWebUserPresenceOAuth", "Poll"), data=form)

    if self.chatState == ChatState.Offline:
        return None

    self.timer(self._chat['interval'] / 1000.0, self._chatPoll)

    if response.status_code != 200:
        logger.error("Error in chat poll: %s", response.status_code)
        response.raise_for_status()
        return None

    body = response.json()

    if body["error"] != "OK":
        logger.warning("Error in chat poll: %s", body["error"])

    self._chat['message'] = body.get("messagelast", "")

    for message in body.get("messages", []):
        sender = SteamID.SteamID(message['accountid_from'])

        type_ = message["type"]
        if type_ == "personastate":
            self._chatUpdatePersona(sender)
        elif type_ == "saytext":
            self.emit('chatMessage', sender, message["text"])
        elif type_ == "typing":
            self.emit('chatTyping', sender)
        else:
            logger.warning("Unhandled message type: %s", type_)


def _loadFriendList(self):
    '''
    Loads friend data
    '''
    form = {
        "access_token": self.oAuthToken,
        "steamid": str(self.steamID)
    }

    response = self.session.get(
        APIUrl("ISteamUserOAuth", "GetFriendList", version="0001"), params=form, headers=self._mobileHeaders)

    if response.status_code != 200:
        logger.error("Load friends error: %s", response.status_code)
        self.timer(2.0, self._loadFriendList)
        return None

    body = response.json()
    if "friends" in body:
        return body["friends"]

    return None


def _chatUpdatePersona(self, steamID):
    '''
    Retrives new persona data if persona event received
    '''
    accnum = steamID.accountid
    response = self.session.get(
        CommunityURL("chat", "friendstate") + str(accnum))

    if response.status_code != 200:
        logger.error("Chat update persona error: %s", response.status_code)
        self.timer(2.0, self._chatUpdatePersona, (steamID))
        return None

    if str(steamID) in self.chatFriends:
        old_persona = self.chatFriends[str(steamID)]
        steamID = old_persona["steamID"]
    else:
        old_persona = {}

    body = response.json()

    persona = {
        "steamID": steamID,
        "personaName": body['m_strName'],
        "personaState": PersonaState(body['m_ePersonaState']),
        "personaStateFlags": PersonaStateFlag(body.get('m_nPersonaStateFlags') or 0),
        "avatarHash": body['m_strAvatarHash'],
        "inGame": body.get('m_bInGame', False),
        "inGameAppID": body.get('m_nInGameAppID', None),
        "inGameName": body.get('m_strInGameName', None)
    }

    self.emit(
        'chatPersonaState', steamID, persona, old_persona)
    self.chatFriends[str(steamID)] = persona
