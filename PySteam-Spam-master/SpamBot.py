import steamapi as SteamAPI
import sys
import time
steam = SteamAPI.SteamAPI()


@steam.event.on('chatMessage')
def chatMessage(sender, text):
    print steam.chatFriends[str(sender.SteamID64)]["personaName"] + ':', text
    if text.lower() == "ping":
        steam.chatMessage(sender, "pong")

#Settings
username = ""
password = ""
victim =  #Steam64ID!
amountofmessages = 100
spammessage = ("Get Spammed!")
timepermessage = 0.1

def spam():
    global victim
    global spammessage
    global timepermessage
    global amountofmessages
    
    for i in range(amountofmessages):
        steam.chatMessage(victim, spammessage)
        time.sleep(timepermessage)
        print "Message Sent!"


status = steam.login(username=username, password=password)
while status != SteamAPI.LoginStatus.LoginSuccessful:
    if status == SteamAPI.LoginStatus.TwoFactor:
        token = raw_input("Two-factor Token: ")
        status = steam.retry(twofactor=token)
    elif status == SteamAPI.LoginStatus.SteamGuard:
        steamguard = raw_input("SteamGuard Code: ")
        status = steam.retry(steamguard=steamguard)
    elif status == SteamAPI.LoginStatus.Captcha:
        captcha = raw_input("CAPTCHA: ")
        status = steam.retry(captcha=captcha)

steam.chatLogon()
spam()
steam.chatLogoff()
