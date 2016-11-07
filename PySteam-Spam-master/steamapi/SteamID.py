import re
import math
from enum import IntEnum, unique


@unique
class Universe(IntEnum):
    INVALID = 0
    PUBLIC = 1
    BETA = 2
    INTERNAL = 3
    DEV = 4


@unique
class Type(IntEnum):
    INVALID = 0
    INDIVIDUAL = 1
    MULTISEAT = 2
    GAMESERVER = 3
    ANON_GAMESERVER = 4
    PENDING = 5
    CONTENT_SERVER = 6
    CLAN = 7
    CHAT = 8
    P2P_SUPER_SEEDER = 9
    ANON_USER = 10


@unique
class Instance(IntEnum):
    ALL = 0
    DESKTOP = 1
    CONSOLE = 2
    WEB = 4


AccountIDMask = 0xFFFFFFFF
AccountInstanceMask = 0x000FFFFF


@unique
class ChatInstanceFlags(IntEnum):
    CLAN = (AccountInstanceMask + 1) >> 1
    LOBBY = (AccountInstanceMask + 1) >> 2
    MMSLOBBY = (AccountInstanceMask + 1) >> 3


class SteamID(object):
    Type = Type
    Universe = Universe
    Instance = Instance
    ChatInstanceFlags = ChatInstanceFlags

    TypeChars = {}
    TypeChars[Type.INVALID] = 'I'
    TypeChars[Type.INDIVIDUAL] = 'U'
    TypeChars[Type.MULTISEAT] = 'M'
    TypeChars[Type.GAMESERVER] = 'G'
    TypeChars[Type.ANON_GAMESERVER] = 'A'
    TypeChars[Type.PENDING] = 'P'
    TypeChars[Type.CONTENT_SERVER] = 'C'
    TypeChars[Type.CLAN] = 'g'
    TypeChars[Type.CHAT] = 'T'
    TypeChars[Type.ANON_USER] = 'a'

    def __init__(self, inp=None):
        self.universe = Universe.INVALID
        self.type = Type.INVALID
        self.instance = Instance.ALL
        self.accountid = 0

        if inp is None:
            return

        inp = str(inp)
        steam2_regex = re.compile(r"^STEAM_([0-5]):([0-1]):([0-9]+)$")
        steam3_regex = re.compile(
            r"^\[([a-zA-Z]):([0-5]):([0-9]+)(:[0-9]+)?\]$")
        if steam2_regex.match(inp):
            # Steam2 ID
            matches = steam2_regex.findall(inp)[0]
            self.universe = Universe(int(matches[1])) or Universe.PUBLIC
            self.type = Type.INDIVIDUAL
            self.instance = Instance.DESKTOP
            self.accountid = (int(matches[2]) * 2) + int(matches[1])
        elif steam3_regex.match(inp):
            matches = steam3_regex.findall(inp)[0]
            self.universe = Universe(int(matches[1]))
            self.accountid = int(matches[2])

            typeChar = matches[0]
            if 0 <= 3 < len(matches) and matches[3]:
                self.instance = int(matches[3][1:] or 0)
                if self.instance in Instance:
                    self.instance = Instance(self.instance)
            elif typeChar == 'U':
                self.instance = Instance.DESKTOP

            if typeChar == 'c':
                self.instance |= ChatInstanceFlags.CLAN
                self.type = Type.CHAT
            elif typeChar == 'L':
                self.instance |= ChatInstanceFlags.LOBBY
                self.type = Type.CHAT
            else:
                self.type = Type(self._getTypeFromChar(typeChar))
        elif not inp.isdigit():
            raise Exception("Not a valid steam format")
        else:
            inp = int(inp)
            if len(str(inp)) == 8:
                inp += 76561197960265728
            self.accountid = int(inp & 0xFFFFFFFF)
            self.instance = Instance((inp >> 32) & 0xFFFFF)
            self.type = Type((inp >> 52) & 0xF)
            self.universe = Universe(inp >> 56)

    def isValid(self):
        if self.type <= Type.INVALID or self.type > Type.ANON_USER:
            return False

        if self.universe <= Universe.INVALID or self.universe > Universe.DEV:
            return False

        if self.type == Type.INDIVIDUAL and ((self.accountid == 0) or self.instance > Instance.WEB):
            return False

        if self.type == Type.CLAN and ((self.accountid == 0) or self.instance != Instance.ALL):
            return False

        if self.type == Type.GAMESERVER and self.accountid == 0:
            return False

        return True

    def Steam2RenderedID(self, newerFormat=None):
        if self.type != Type.INDIVIDUAL:
            raise Exception(
                "Can't get Steam2 rendered ID for non-individual ID")
        else:
            universe = self.universe
            if not newerFormat and universe == 1:
                universe = 0

            return "STEAM_{x}:{y}:{z}".format(x=universe, y=(self.accountid & 1), z=int(math.floor(self.accountid / 2)))

    def Steam3RenderedID(self):
        typeChar = self.TypeChars.get(self.type, 'i')

        if self.instance & ChatInstanceFlags.CLAN:
            typeChar = 'c'
        elif self.instance & ChatInstanceFlags.LOBBY:
            typeChar = 'L'

        renderInstance = ((self.type == Type.ANON_GAMESERVER) or (self.type == Type.MULTISEAT) or (
            self.type == Type.INDIVIDUAL and self.instance != Instance.DESKTOP))

        return "[{typechar}:{universe}:{accid}{instance}]".format(
            typechar=typeChar,
            universe=self.universe,
            accid=self.accountid,
            instance=(':' + str(self.instance) if renderInstance else ''))

    @property
    def SteamID64(self):
        return ((self.universe << 56) | (self.type << 52) | (self.instance << 32) | self.accountid)

    @property
    def SteamID32(self):
        return (self.SteamID64 - 76561197960265728)

    @property
    def SteamID(self):
        return self.Steam2RenderedID()

    @property
    def SteamID3(self):
        return self.Steam3RenderedID()

    def __str__(self):
        return str(self.SteamID64)

    def __repr__(self):
        return "SteamID.SteamID('{}')".format(self.SteamID64)

    def _getTypeFromChar(self, typeChar):
        for type_ in self.TypeChars:
            if self.TypeChars[type_] == typeChar:
                return int(type_)

        return self.Type.INVALID
