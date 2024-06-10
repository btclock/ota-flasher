import concurrent.futures
import logging
import traceback

import serial
from app.gui.action_button_panel import ActionButtonPanel
from app.release_checker import ReleaseChecker
import wx
import wx.richtext as rt

from zeroconf import ServiceBrowser, Zeroconf
import os
import webbrowser

from app import espota
from app.api import ApiHandler
from app.fw_updater import FwUpdater
from app.gui.devices_panel import DevicesPanel
from app.utils import get_app_data_folder
from app.zeroconf_listener import ZeroconfListener

from app.espota import FLASH, SPIFFS

class BTClockOTAApp(wx.App):
    def OnInit(self):
        return True
class RichTextCtrlHandler(logging.Handler):
    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl

    def emit(self, record):
        msg = self.format(record)
        wx.CallAfter(self.append_text, "\n" + msg)

    def append_text(self, text):
        self.ctrl.AppendText(text)
        self.ctrl.ShowPosition(self.ctrl.GetLastPosition())
        
class SerialPortsComboBox(wx.ComboBox):
    def __init__(self, parent, fw_update):
        self.fw_update = fw_update
        self.ports = serial.tools.list_ports.comports()
        wx.ComboBox.__init__(self, parent, choices=[
                             port.device for port in self.ports])


class BTClockOTAUpdater(wx.Frame):
    updatingName = ""

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(800, 500))

        self.SetMinSize((800, 500))
        self.releaseChecker = ReleaseChecker()
        self.zeroconf = Zeroconf()
        self.listener = ZeroconfListener(self.on_zeroconf_state_change)
        self.browser = ServiceBrowser(
            self.zeroconf, "_http._tcp.local.", self.listener)
        self.api_handler = ApiHandler()
        self.fw_updater = FwUpdater(self.call_progress, self.SetStatusText)
        

        panel = wx.Panel(self)
        self.log_ctrl = rt.RichTextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        monospace_font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.log_ctrl.SetFont(monospace_font)

        handler = RichTextCtrlHandler(self.log_ctrl)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.DEBUG)

        
        self.device_list = DevicesPanel(panel)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.device_list, proportion=2,
                 flag=wx.EXPAND | wx.ALL, border=20)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.fw_label = wx.StaticText(
            panel, label=f"Fetching latest version from GitHub...")
        hbox.Add(self.fw_label,  1, wx.EXPAND | wx.ALL, 5)

        self.actionButtons = ActionButtonPanel(
            panel, self)
        hbox.AddStretchSpacer()

        hbox.Add(self.actionButtons, 2, wx.EXPAND | wx.ALL, 5)
        vbox.Add(hbox, 0, wx.EXPAND | wx.ALL, 20)

        self.progress_bar = wx.Gauge(panel, range=100)
        vbox.Add(self.progress_bar, 0, wx.EXPAND | wx.ALL, 20)
        vbox.Add(self.log_ctrl, 1, flag=wx.EXPAND | wx.ALL, border=20)

        panel.SetSizer(vbox)
        self.setup_ui()

        wx.CallAfter(self.fetch_latest_release_async)
        wx.YieldIfNeeded()
    def setup_ui(self):
        self.setup_menubar()
        self.status_bar = self.CreateStatusBar(2)
        self.Show(True)
        self.Centre()

    def setup_menubar(self):
        filemenu = wx.Menu()
        menuOpenDownloadDir = filemenu.Append(
            wx.ID_OPEN, "&Open Download Dir", " Open the directory with firmware files and cache")
        menuAbout = filemenu.Append(
            wx.ID_ABOUT, "&About", " Information about this program")
        menuExit = filemenu.Append(
            wx.ID_EXIT, "E&xit", " Terminate the program")

        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, "&File")

        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU, self.OnOpenDownloadFolder, menuOpenDownloadDir)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)

    def on_zeroconf_state_change(self, type, name, state, info):
        index = self.device_list.FindItem(0, name)

        if state == "Added":
            deviceSettings = self.api_handler.get_settings(
                info.parsed_addresses()[0])

            version = info.properties.get(b"rev").decode()
            fsHash = "Too old"
            hwRev = "REV_A_EPD_2_13"

            if 'gitTag' in deviceSettings:
                version = deviceSettings["gitTag"]

            if 'fsRev' in deviceSettings:
                fsHash = deviceSettings['fsRev'][:7]

            if (info.properties.get(b"hw_rev") is not None):
                hwRev = info.properties.get(b"hw_rev").decode()

            fwHash = info.properties.get(b"rev").decode()[:7]
            address = info.parsed_addresses()[0]

            if index == wx.NOT_FOUND:
                index = self.device_list.InsertItem(
                    self.device_list.GetItemCount(), type)
                self.device_list.SetItem(index, 0, name)
                self.device_list.SetItem(index, 1, version)
                self.device_list.SetItem(index, 2, fwHash)
                self.device_list.SetItem(index, 3, hwRev)
                self.device_list.SetItem(index, 4, address)

            else:
                self.device_list.SetItem(index, 0, name)
                self.device_list.SetItem(index, 1, version)
                self.device_list.SetItem(index, 2, fwHash)
                self.device_list.SetItem(index, 3, hwRev)
                self.device_list.SetItem(index, 4, address)
            self.device_list.SetItem(index, 5, fsHash)
            self.device_list.SetItemData(index, index)
            self.device_list.itemDataMap[index] = [
                name, version, fwHash, hwRev, address, fsHash]
            for col in range(0, len(self.device_list.column_headings)):
                self.device_list.SetColumnWidth(
                    col, wx.LIST_AUTOSIZE_USEHEADER)
        elif state == "Removed":
            if index != wx.NOT_FOUND:
                self.device_list.DeleteItem(index)

    def call_progress(self, progress):
        progressPerc = int(progress*100)
        self.SetStatusText(f"Progress: {progressPerc}%")
        wx.CallAfter(self.update_progress, progress)

    def update_progress(self, progress):
        progressPerc = int(progress*100)
        self.progress_bar.SetValue(progressPerc)
        wx.YieldIfNeeded()

    def fetch_latest_release_async(self):
        # Start a new thread to execute fetch_latest_release
        app_folder = get_app_data_folder()
        if not os.path.exists(app_folder):
            os.makedirs(app_folder)
        executor = concurrent.futures.ThreadPoolExecutor()
        future = executor.submit(self.releaseChecker.fetch_latest_release)
        future.add_done_callback(self.handle_latest_release)

    def handle_latest_release(self, future):
        try:
            latest_release = future.result()
            self.fw_label.SetLabelText(f"Downloaded firmware version: {
                                       latest_release}\nCommit: {self.releaseChecker.commit_hash}")
        except Exception as e:
            self.fw_label.SetLabel(f"Error occurred: {str(e)}")
            traceback.print_tb(e.__traceback__)
            
    def OnOpenDownloadFolder(self, e):
        wx.LaunchDefaultBrowser(get_app_data_folder())
            
    def OnAbout(self, e):
        dlg = wx.MessageDialog(
            self, "An updater for BTClocks", "About BTClock OTA Updater", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnExit(self, e):
        self.Close(False)
