from app.main import BTClockOTAUpdater
import wx

if __name__ == "__main__":
    app = wx.App(False)
    frame = BTClockOTAUpdater(None, 'BTClock OTA updater')
    
    app.MainLoop()
