import wx
from zeroconf import Zeroconf


class ZeroconfListener:
    '''Zeroconf Handler to find BTClocks in the network'''
    release_name = ""
    firmware_file = ""

    def __init__(self, update_callback):
        self.update_callback = update_callback
     #   self.update_service = update_callback
        self.services = {}

    def update_service(self, zc: Zeroconf, type: str, name: str) -> None:
        if (name.startswith('btclock-')):
            info = zc.get_service_info(type, name)
            self.services[name] = info
            wx.CallAfter(self.update_callback, type, name, "Added", info)

    def remove_service(self, zeroconf, type, name):
        if name in self.services:
            del self.services[name]

        wx.CallAfter(self.update_callback, type, name, "Removed")

    def add_service(self, zeroconf, type, name):
        if (name.startswith('btclock-')):
            info = zeroconf.get_service_info(type, name)
            self.services[name] = info
            wx.CallAfter(self.update_callback, type, name, "Added", info)
