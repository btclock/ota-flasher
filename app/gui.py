import random
from threading import Thread
import threading
import serial
import wx
import wx.lib.mixins.listctrl

from zeroconf import ServiceBrowser, Zeroconf
import requests
import os
import webbrowser

from app import espota
from app.api import ApiHandler
from app.fw_update import FwUpdate
from app.zeroconf_listener import ZeroconfListener

from app.espota import FLASH,SPIFFS

class SerialPortsComboBox(wx.ComboBox):
    def __init__(self, parent, fw_update):
        self.fw_update = fw_update
        self.ports = serial.tools.list_ports.comports()
        wx.ComboBox.__init__(self,parent, choices=[port.device for port in self.ports])

class DevicesPanel(wx.ListCtrl,wx.lib.mixins.listctrl.ColumnSorterMixin,    wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin,
):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        self.column_headings = ["name", "Version", "SW Revision", "HW Revision", "IP", "FS Version"]
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(
            self,
            len(self.column_headings),
        )
        wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin.__init__(self)

        for column, heading in enumerate(self.column_headings):
            self.AppendColumn(heading)

        self.itemDataMap = {}
        
    def OnSortOrderChanged(self):
        """Method to handle changes to the sort order"""

        column, ascending = self.GetSortState()
        self.ShowSortIndicator(column, ascending)
        self.SortListItems(column, ascending)

    def GetListCtrl(self):
        """Method required by the ColumnSorterMixin"""
        return self
    
class BTClockOTAUpdater(wx.Frame):
    release_name = ""
    commit_hash = ""
    currentlyUpdating = False
    updatingName = ""

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(800,500))
        self.SetMinSize((800,500))
        ubuntu_it = wx.Font(32, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, faceName="Ubuntu")
        # "Ubuntu-RI.ttf")
     
        self.fw_update = FwUpdate()

        panel = wx.Panel(self)

        self.title = wx.StaticText(panel, label="BTClock OTA firmware updater")
        self.title.SetFont(ubuntu_it)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.title, 0, wx.EXPAND | wx.ALL, 20, 0)

        # serialPorts = SerialPortsComboBox(panel, self.fw_update)
        # vbox.Add(serialPorts, 0, wx.EXPAND | wx.ALL, 20, 0)

        self.device_list = DevicesPanel(panel)
        self.device_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.device_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_item_deselected)

        vbox.Add(self.device_list, proportion = 2, flag=wx.EXPAND | wx.ALL, border = 20)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        bbox = wx.BoxSizer(wx.HORIZONTAL)

        gs = wx.GridSizer(1, 4, 1, 1)

        self.fw_label = wx.StaticText(panel, label=f"Checking latest version...")
        self.update_button = wx.Button(panel, label="Update Firmware")
        self.update_button.Bind(wx.EVT_BUTTON, self.on_click_update_firmware)
        self.update_fs_button = wx.Button(panel, label="Update Filesystem")
        self.update_fs_button.Bind(wx.EVT_BUTTON, self.on_click_update_fs)

        self.identify_button = wx.Button(panel, label="Identify")
        self.identify_button.Bind(wx.EVT_BUTTON, self.on_click_identify)
        self.open_webif_button = wx.Button(panel, label="Open WebUI")
        self.open_webif_button.Bind(wx.EVT_BUTTON, self.on_click_webui)
        self.update_button.Disable()
        self.update_fs_button.Disable()
        self.identify_button.Disable()
        self.open_webif_button.Disable()

        hbox.Add(self.fw_label,  1, wx.EXPAND | wx.ALL, 5)
        bbox.Add(self.update_button)
        bbox.Add(self.update_fs_button)
        bbox.Add(self.identify_button)
        bbox.Add(self.open_webif_button)

        hbox.AddStretchSpacer()
        hbox.Add(bbox, 2, wx.EXPAND | wx.ALL, 5)
        vbox.Add(hbox, 0, wx.EXPAND | wx.ALL, 20)

        self.progress_bar = wx.Gauge(panel, range=100)
        vbox.Add(self.progress_bar, 0, wx.EXPAND | wx.ALL, 20)

        panel.SetSizer(vbox)

        filemenu= wx.Menu()
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

    

        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.status_bar = self.CreateStatusBar(2)        
        # self.StatusBar.SetFieldsCount(2)  
#        self.StatusBar.SetStatusWidths(-3, -1)
        self.Show(True)

        self.zeroconf = Zeroconf()
        self.listener = ZeroconfListener(self.on_zeroconf_state_change)
        self.browser = ServiceBrowser(self.zeroconf, "_http._tcp.local.", self.listener)
        self.api_handler = ApiHandler()

        wx.CallAfter(self.fetch_latest_release)

    def on_item_selected(self, event):
        self.update_button.Enable()
        self.update_fs_button.Enable()
        self.identify_button.Enable()
        self.open_webif_button.Enable()

    def on_item_deselected(self, event):
        if self.device_list.GetFirstSelected() == -1:
            self.update_button.Disable()
            self.update_fs_button.Disable()
            self.identify_button.Disable()
            self.open_webif_button.Disable()

    def on_zeroconf_state_change(self, type, name, state, info):
        index = self.device_list.FindItem(0, name)

        if state == "Added":
            if index == wx.NOT_FOUND:
                index = self.device_list.InsertItem(self.device_list.GetItemCount(), type)
                self.device_list.SetItem(index, 0, name)
                self.device_list.SetItem(index, 1, info.properties.get(b"version").decode())
                self.device_list.SetItem(index, 2, info.properties.get(b"rev").decode())
                if (info.properties.get(b"hw_rev") is not None):
                    self.device_list.SetItem(index, 3, info.properties.get(b"hw_rev").decode())
                self.device_list.SetItem(index, 4, info.parsed_addresses()[0])

            else:
                self.device_list.SetItem(index, 0, name)
                self.device_list.SetItem(index, 1, info.properties.get(b"version").decode())
                self.device_list.SetItem(index, 2, info.properties.get(b"rev").decode())
                if (info.properties.get(b"hw_rev").decode()):
                    self.device_list.SetItem(index, 3, info.properties.get(b"hw_rev").decode())
                self.device_list.SetItem(index, 4, info.parsed_addresses()[0])
            self.device_list.SetItem(index, 5, self.api_handler.check_fs_hash(info.parsed_addresses()[0]))
            self.device_list.SetItemData(index, index)
            self.device_list.itemDataMap[index] = [name, info.properties.get(b"version").decode(), info.properties.get(b"rev").decode(), info.properties.get(b"hw_rev").decode(), info.parsed_addresses()[0]]
            for col in range(0, len(self.device_list.column_headings)):
                self.device_list.SetColumnWidth(col, wx.LIST_AUTOSIZE_USEHEADER)
        elif state == "Removed":
            if index != wx.NOT_FOUND:
                self.device_list.DeleteItem(index)
    
    def on_click_update_firmware(self, event):
        selected_index = self.device_list.GetFirstSelected()
        if selected_index != -1:
            service_name = self.device_list.GetItemText(selected_index, 0)
            hw_rev = self.device_list.GetItemText(selected_index, 3)

            info = self.listener.services.get(service_name)
            if info:
                address = info.parsed_addresses()[0] if info.parsed_addresses() else "N/A"
                self.start_firmware_update(address, hw_rev)
            else:
                wx.MessageBox("No service information available for selected device", "Error", wx.ICON_ERROR)
        else:
            wx.MessageBox("Please select a device to update", "Error", wx.ICON_ERROR)

    def on_click_webui(self, event):
        selected_index = self.device_list.GetFirstSelected()
        if selected_index != -1:
            service_name = self.device_list.GetItemText(selected_index, 0)
            info = self.listener.services.get(service_name)
            if info:
                address = info.parsed_addresses()[0] if info.parsed_addresses() else "N/A"
                thread = threading.Thread(target=lambda: webbrowser.open(f"http://{address}"))
                thread.start()

    def run_fs_update(self, address, firmware_file, type):
        global PROGRESS
        PROGRESS = True
        espota.PROGRESS = True
        global TIMEOUT
        TIMEOUT = 10
        espota.TIMEOUT = 10

        espota.serve(address, "0.0.0.0", 3232, random.randint(10000,60000), "", firmware_file, type, self.call_progress)

        wx.CallAfter(self.update_progress, 100)
        self.currentlyUpdating = False
        self.SetStatusText(f"Finished!")    

    def call_progress(self, progress):
        progressPerc = int(progress*100)
        self.SetStatusText(f"{self.updatingName} - Progress: {progressPerc}%")
        wx.CallAfter(self.update_progress, progress)

    def update_progress(self, progress):
        self.progress_bar.SetValue(int(progress*100))
        wx.YieldIfNeeded()

    def on_click_update_fs(self, event):
        selected_index = self.device_list.GetFirstSelected()
        if selected_index != -1:
            service_name = self.device_list.GetItemText(selected_index, 0)
            info = self.listener.services.get(service_name)
            if self.currentlyUpdating:
                wx.MessageBox("Please wait, already updating", "Error", wx.ICON_ERROR)
                return

            if info:
                address = info.parsed_addresses()[0] if info.parsed_addresses() else "N/A"
                self.start_fs_update(address)
            else:
                wx.MessageBox("No service information available for selected device", "Error", wx.ICON_ERROR)
        else:
            wx.MessageBox("Please select a device to update", "Error", wx.ICON_ERROR)

    def start_firmware_update(self, address, hw_rev):
        self.SetStatusText(f"Starting firmware update")

        model_name = "lolin_s3_mini_213epd"
        if (hw_rev == "REV_B_EPD_2_13"):
            model_name = "btclock_rev_b_213epd"

        local_filename = f"firmware/{self.release_name}_{model_name}_firmware.bin"

        self.updatingName = address
        self.currentlyUpdating = True

        if os.path.exists(os.path.abspath(local_filename)):
            thread = Thread(target=self.run_fs_update, args=(address, os.path.abspath(local_filename), FLASH))
            thread.start()

    def start_fs_update(self, address):
        # Path to the firmware file
        self.SetStatusText(f"Starting filesystem update")
        local_filename = f"firmware/{self.release_name}_littlefs.bin"

        self.updatingName = address
        self.currentlyUpdating = True

        if os.path.exists(os.path.abspath(local_filename)):
            thread = Thread(target=self.run_fs_update, args=(address, os.path.abspath(local_filename), SPIFFS))
            thread.start()

        wx.CallAfter(self.update_progress, 100)

    def on_click_identify(self, event):
        selected_index = self.device_list.GetFirstSelected()
        if selected_index != -1:
            service_name = self.device_list.GetItemText(selected_index, 0)
            info = self.listener.services.get(service_name)
            if info:
                address = info.parsed_addresses()[0] if info.parsed_addresses() else "N/A"
                port = info.port
                self.api_handler.identify_btclock(address)
            else:
                wx.MessageBox("No service information available for selected device", "Error", wx.ICON_ERROR)
        else:
            wx.MessageBox("Please select a device to make an API call", "Error", wx.ICON_ERROR)

    def fetch_latest_release(self):
        repo = "btclock/btclock_v3"

        filenames_to_download = ["lolin_s3_mini_213epd_firmware.bin", "btclock_rev_b_213epd_firmware.bin", "littlefs.bin"]
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            response = requests.get(url)
            response.raise_for_status()
            latest_release = response.json()
            release_name = latest_release['tag_name']
            self.release_name = release_name


            asset_url = None
            asset_urls = []
            for asset in latest_release['assets']:
                if asset['name'] in filenames_to_download:
                    asset_urls.append(asset['browser_download_url'])
            if asset_urls:
                for asset_url in asset_urls:
                    self.download_file(asset_url, release_name)
                ref_url = f"https://api.github.com/repos/{repo}/git/ref/tags/{release_name}"
                response = requests.get(ref_url)
                response.raise_for_status()
                ref_info = response.json()
                if (ref_info["object"]["type"] == "commit"):
                    self.commit_hash = ref_info["object"]["sha"]
                else:
                    tag_url = f"https://api.github.com/repos/{repo}/git/tags/{ref_info["object"]["sha"]}"
                    response = requests.get(tag_url)
                    response.raise_for_status()
                    tag_info = response.json()
                    self.commit_hash = tag_info["object"]["sha"]

                self.fw_label.SetLabelText(f"Downloaded firmware version: {self.release_name}\nCommit: {self.commit_hash}")


            else:
                wx.CallAfter(self.SetStatusText, f"File {filenames_to_download} not found in latest release")
        except requests.RequestException as e:
            wx.CallAfter(self.SetStatusText, f"Error fetching release: {e}")



    def download_file(self, url, release_name):
        local_filename = f"{release_name}_{url.split('/')[-1]}"
        response = requests.get(url, stream=True)
        total_length = response.headers.get('content-length')

        if os.path.exists(f"firmware/{local_filename}"):
            wx.CallAfter(self.SetStatusText, f"{local_filename} is already downloaded")
            return
        
        if total_length is None:
            wx.CallAfter(self.SetStatusText, "No content length header")
        else:
            total_length = int(total_length)
            chunk_size = 1024
            num_chunks = total_length // chunk_size
            with open(f"firmware/{local_filename}", 'wb') as f:
                for i, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        progress = int((i / num_chunks) * 100)
                        wx.CallAfter(self.update_progress, progress)

            wx.CallAfter(self.update_progress, 100)
            wx.CallAfter(self.SetStatusText, "Download completed") 

    def OnAbout(self,e):
        dlg = wx.MessageDialog( self, "An updater for BTClocks", "About BTClock OTA Updater", wx.OK)
        dlg.ShowModal() 
        dlg.Destroy() 

    def OnExit(self,e):
        self.Close(False)  