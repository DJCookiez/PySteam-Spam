from Crypto import Random
import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(40)


def CommunityURL(namespace, method):
    return "https://steamcommunity.com/{namespace}/{method}/".format(namespace=namespace, method=method)


def APIUrl(namespace, method, version="1"):
    return 'https://api.steampowered.com/{namespace}/{method}/v{version}/'.format(namespace=namespace, method=method, version=version)


def generateSessionID():
    '''
    Generates a "random" session ID for Steam
    '''
    return Random.get_random_bytes(12).encode('hex')


def urlForAvatarHash(hashed, quality="full"):
    '''
    Provides the URL for a steam avatar, given the avatar hash
    '''
    if quality == "icon":
        quality = ""
    else:
        quality = '_' + quality

    if hashed == ("0" * 40):
        hashed = 'fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb'

    tag = hashed[:2]
    return "http://cdn.akamai.steamstatic.com/steamcommunity/public/images/avatars/{tag}/{hash}{quality}.jpg".format(
        tag=tag, hash=hashed, quality=quality)


def dictDiff(a, b):
    '''
    Returns the changes between two dicts
    '''
    diff = {}

    for key in a.keys():
        if key in b:
            if b[key] != a[key]:
                diff[key] = a[key]
        else:
            diff[key] = a[key]

    return diff
