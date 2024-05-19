import wx

from app.gui import BTClockOTAUpdater

app = wx.App(False)
frame = BTClockOTAUpdater(None, 'BTClock OTA updater')
app.MainLoop()