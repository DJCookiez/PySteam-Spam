import SteamID
from enum import Enum, IntEnum, unique
from . import *
from pyquery import PyQuery as pq
import os


class StrEnum(str, Enum):
    pass


@unique
class PrivacyState(IntEnum):
    Private, FriendsOnly, Public = range(1, 4)


@unique
class CommentPrivacyState(StrEnum):
    Private, FriendsOnly, Public = [
        "commentselfonly",
        "commentfriendsonly",
        "commentanyone"
    ]


def setupProfile(self):
    ''' Initiates a new Steam Profile '''
    resp = self.session.get(
        CommunityURL('profiles', str(self.steamID)) + 'edit?welcomed=1')
    return resp and resp.status_code == 200


def editProfile(self, new_values=None):
    '''
    Allows changes to your Steam profile information.
    Current values are returned if `new_values` is not supplied.
    Supported values for editing are:
        - `personaName`
        - `real_name`
        - `country`
        - `state`
        - `city`
        - `customURL`
        - `summary`
        - `profile_background`
        - `primary_group_steamid`
    '''
    def editables(values):
        valid = ['personaName', 'real_name', 'country', 'state', 'city',
                 'customURL', 'summary', 'profile_background', 'primary_group_steamid']

        return {k: v for k, v in values.items() if k in valid}

    def parseForValues(doc):
        values = {}

        all_inputs = doc('#editForm :input').filter(
            lambda i, this: this.tag != "button")
        # visible = all_inputs.filter("[type!='hidden']")
        without_file = all_inputs.filter("[type!='file']")

        for inp in without_file:
            values[inp.name] = inp.value

        return values

    edit_url = CommunityURL('profiles', str(self.steamID)) + 'edit'
    doc = pq(self.session.get(edit_url).text)

    values = parseForValues(doc)

    if not new_values:
        return editables(values)
    else:
        values.update(new_values)
        update_resp = pq(self.session.post(edit_url, data=values).text)
        values = parseForValues(update_resp)
        error = update_resp('#errorText .formRowFields')
        if error:
            return (error.text.strip(), editables(values))

        return (None, editables(values))


def profileSettings(self, new_values=None):
    '''
    Allows changes to your Steam permissions.
    Current values are returned if `new_values` is not supplied.
    Supported values for editing are:
        - `privacySetting`
        - `commentSetting`
        - `inventoryPrivacySetting`
        - `inventoryGiftPrivacy`
    '''
    def editables(values):
        valid = ['privacySetting', 'commentSetting',
                 'inventoryPrivacySetting', 'inventoryGiftPrivacy']

        return {k: v for k, v in values.items() if k in valid}

    def parseForValues(doc):
        all_inputs = doc('#editForm :input').filter(
            lambda i, this: this.tag != "button")

        values = {inp.name: inp.value for inp in all_inputs}

        for inp in doc('#editForm input:checked'):
            values[inp.name] = inp.value
            if inp.name in ['privacySetting', 'inventoryPrivacySetting']:
                values[inp.name] = PrivacyState(int(inp.value))
            if inp.name == 'commentSetting':
                values[inp.name] = CommentPrivacyState(inp.value)

        if values['inventoryGiftPrivacy'] is not None:
            values['inventoryGiftPrivacy'] = bool(
                int(values['inventoryGiftPrivacy']))
        else:
            values['inventoryGiftPrivacy'] = False

        return values

    edit_url = CommunityURL('profiles', str(self.steamID)) + 'edit/settings'
    doc = pq(self.session.get(edit_url).text)
    values = parseForValues(doc)

    if not new_values:
        return editables(values)
    else:
        values.update(new_values)
        for k, v in editables(values).items():
            if k == 'inventoryGiftPrivacy':
                values[k] = int(v)
            else:
                values[k] = v.value

        resp = self.session.post(edit_url, data=values)
        update_resp = pq(resp.text)
        values = parseForValues(update_resp)
        error = update_resp('#errorText .formRowFields')
        if error:
            return (error.text.strip(), editables(values))

        print values
        return (None, editables(values))


def uploadAvatar(self, image):
    '''
    Sets the current account's avatar on Steam.
    `image` should be a file-like object, in binary mode.
    '''
    data = {
        'MAX_FILE_SIZE': 1048576,
        'type': 'player_avatar_image',
        'sId': self.steamID.SteamID64,
        'sessionid': self.sessionID,
        'doSub': 1,
        'json': 1
    }
    files = {'avatar': image}
    resp = self.session.post(CommunityURL('actions', 'FileUploader'), files=files, data=data)

    if resp.status_code != 200:
        logger.error('HTTP error %s', resp.status_code)
        return

    body = resp.json()
    if not body or not body.get('success'):
        logger.error('Malformed response')
        return

    if not body.get('success') and body.get('message'):
        logger.error(body['message'])
        return

    return body