import wx

from app.main import BTClockOTAUpdater

app = wx.App(False)
frame = BTClockOTAUpdater(None, 'BTClock OTA updater')
app.MainLoop()