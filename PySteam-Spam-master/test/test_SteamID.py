import steamapi.SteamID as SteamID
import pytest


def test_parameterless_construction():
    sid = SteamID.SteamID()
    assert sid.universe == SteamID.Universe.INVALID
    assert sid.type == SteamID.Type.INVALID
    assert sid.instance == SteamID.Instance.ALL
    assert sid.accountid == 0


def test_steam2id_construction_universe_0():
    sid = SteamID.SteamID('STEAM_0:0:23071901')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143802


def test_steam2id_construction_universe_1():
    sid = SteamID.SteamID('STEAM_1:1:23071901')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143803


def test_steam3id_construction_individual():
    sid = SteamID.SteamID('[U:1:46143802]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143802


def test_steam3id_construction_gameserver():
    sid = SteamID.SteamID('[G:1:31]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.GAMESERVER
    assert sid.instance == SteamID.Instance.ALL
    assert sid.accountid == 31


def test_steam3id_construction_anon_gameserver():
    sid = SteamID.SteamID('[A:1:46124:11245]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.ANON_GAMESERVER
    assert sid.instance == 11245
    assert sid.accountid == 46124


def test_steam3id_construction_lobby():
    sid = SteamID.SteamID('[L:1:12345]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.CHAT
    assert sid.instance == SteamID.ChatInstanceFlags.LOBBY
    assert sid.accountid == 12345


def test_steam3id_construction_lobby_with_instanceid():
    sid = SteamID.SteamID('[L:1:12345:55]')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.CHAT
    assert sid.instance == SteamID.ChatInstanceFlags.LOBBY | 55
    assert sid.accountid == 12345


def test_steamid64_construction_individual():
    sid = SteamID.SteamID('76561198006409530')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143802


def test_steamid64_construction_clan():
    sid = SteamID.SteamID('103582791434202956')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.CLAN
    assert sid.instance == SteamID.Instance.ALL
    assert sid.accountid == 4681548


def test_steamid32_construction_individual():
    sid = SteamID.SteamID('46143802')
    assert sid.universe == SteamID.Universe.PUBLIC
    assert sid.type == SteamID.Type.INDIVIDUAL
    assert sid.instance == SteamID.Instance.DESKTOP
    assert sid.accountid == 46143802


def test_invalid_construction():
    with pytest.raises(Exception):
        SteamID.SteamID('invalid input')


def test_steam2id_rendering_universe_0():
    sid = SteamID.SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.INDIVIDUAL
    sid.instance = SteamID.Instance.DESKTOP
    sid.accountid = 46143802
    assert sid.SteamID == "STEAM_0:0:23071901"
    assert sid.Steam2RenderedID() == "STEAM_0:0:23071901"


def test_steam2id_rendering_universe_1():
    sid = SteamID.SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.INDIVIDUAL
    sid.instance = SteamID.Instance.DESKTOP
    sid.accountid = 46143802
    assert sid.Steam2RenderedID(True) == "STEAM_1:0:23071901"


def test_steam2id_rendering_non_individual():
    with pytest.raises(Exception):
        sid = SteamID.SteamID()
        sid.universe = SteamID.Universe.PUBLIC
        sid.type = SteamID.Type.CLAN
        sid.instance = SteamID.Instance.DESKTOP
        sid.accountid = 4681548
        sid.Steam2RenderedID()


def test_steam3id_rendering_individual():
    sid = SteamID.SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.INDIVIDUAL
    sid.instance = SteamID.Instance.DESKTOP
    sid.accountid = 46143802
    assert sid.Steam3RenderedID() == "[U:1:46143802]"
    assert sid.SteamID3 == "[U:1:46143802]"


def test_steam3id_rendering_anon_gameserver():
    sid = SteamID.SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.ANON_GAMESERVER
    sid.instance = 41511
    sid.accountid = 43253156
    assert sid.Steam3RenderedID() == "[A:1:43253156:41511]"
    assert sid.SteamID3 == "[A:1:43253156:41511]"


def test_steam3id_rendering_lobby():
    sid = SteamID.SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.CHAT
    sid.instance = SteamID.ChatInstanceFlags.LOBBY
    sid.accountid = 451932
    assert sid.Steam3RenderedID() == "[L:1:451932]"
    assert sid.SteamID3 == "[L:1:451932]"


def test_steamid64_rendering_individual():
    sid = SteamID.SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.INDIVIDUAL
    sid.instance = SteamID.Instance.DESKTOP
    sid.accountid = 46143802
    assert sid.SteamID64 == 76561198006409530L


def test_steamid64_anon_gameserver():
    sid = SteamID.SteamID()
    sid.universe = SteamID.Universe.PUBLIC
    sid.type = SteamID.Type.ANON_GAMESERVER
    sid.instance = 188991
    sid.accountid = 42135013
    assert sid.SteamID64 == 90883702753783269L


def test_invalid_new_id():
    sid = SteamID.SteamID()
    assert sid.isValid() is False


def test_invalid_individual_instance():
    sid = SteamID.SteamID('[U:1:46143802:10]')
    assert sid.isValid() is False


def test_invalid_non_all_clan_instance():
    sid = SteamID.SteamID('[g:1:4681548:2]')
    assert sid.isValid() is False


def test_invalid_gameserver_id_with_accountid_0():
    sid = SteamID.SteamID('[G:1:0]')
    assert sid.isValid() is False
