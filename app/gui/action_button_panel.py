import threading
import webbrowser
from app.api import ApiHandler
from app.gui.devices_panel import DevicesPanel
from app.zeroconf_listener import ZeroconfListener
import wx

class ActionButtonPanel(wx.Panel):
    currentlyUpdating = False

    def __init__(self, parent:wx.Panel, parent_frame:wx.Frame, *args, **kwargs):
        super(ActionButtonPanel, self).__init__(parent, *args, **kwargs)
        
        self.parent = parent
        self.parent_frame = parent_frame
        self.api_handler:ApiHandler = parent_frame.api_handler
        self.device_list:DevicesPanel = parent_frame.device_list
        self.listener:ZeroconfListener = parent_frame.listener

        self.device_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.device_list.Bind(wx.EVT_LIST_ITEM_DESELECTED,
                              self.on_item_deselected)
        self.InitUI()
    
    def InitUI(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.update_button = wx.Button(self, label="Update Firmware")
        self.update_button.Bind(wx.EVT_BUTTON, self.on_click_update_firmware)
        self.update_fs_button = wx.Button(self, label="Update Filesystem")
        self.update_fs_button.Bind(wx.EVT_BUTTON, self.on_click_update_fs)

        self.identify_button = wx.Button(self, label="Identify")
        self.identify_button.Bind(wx.EVT_BUTTON, self.on_click_identify)
        self.open_webif_button = wx.Button(self, label="Open WebUI")
        self.open_webif_button.Bind(wx.EVT_BUTTON, self.on_click_webui)
        self.update_button.Disable()
        self.update_fs_button.Disable()
        self.identify_button.Disable()
        self.open_webif_button.Disable()
        
        sizer.Add(self.update_button)
        sizer.Add(self.update_fs_button)
        sizer.Add(self.identify_button)
        sizer.Add(self.open_webif_button)
        
        self.SetSizer(sizer)
        
    def on_click_update_firmware(self, event):
        selected_index = self.device_list.GetFirstSelected()
        if selected_index != -1:
            service_name = self.device_list.GetItemText(selected_index, 0)
            hw_rev = self.device_list.GetItemText(selected_index, 3)

            info = self.listener.services.get(service_name)
            if info:
                address = info.parsed_addresses(
                )[0] if info.parsed_addresses() else "N/A"
                self.parent_frame.fw_updater.start_firmware_update(self.parent_frame.releaseChecker.release_name, address, hw_rev)
            else:
                wx.MessageBox(
                    "No service information available for selected device", "Error", wx.ICON_ERROR)
        else:
            wx.MessageBox("Please select a device to update",
                          "Error", wx.ICON_ERROR)

    def on_click_webui(self, event):
        selected_index = self.device_list.GetFirstSelected()
        if selected_index != -1:
            service_name = self.device_list.GetItemText(selected_index, 0)
            info = self.listener.services.get(service_name)
            if info:
                address = info.parsed_addresses(
                )[0] if info.parsed_addresses() else "N/A"
                thread = threading.Thread(
                    target=lambda: webbrowser.open(f"http://{address}"))
                thread.start()
                
    def on_click_update_fs(self, event):
        selected_index = self.device_list.GetFirstSelected()
        if selected_index != -1:
            service_name = self.device_list.GetItemText(selected_index, 0)
            info = self.listener.services.get(service_name)
            if self.currentlyUpdating:
                wx.MessageBox("Please wait, already updating",
                              "Error", wx.ICON_ERROR)
                return

            if info:
                address = info.parsed_addresses(
                )[0] if info.parsed_addresses() else "N/A"
                self.parent_frame.fw_updater.start_fs_update(self.parent_frame.releaseChecker.release_name, address)
            else:
                wx.MessageBox(
                    "No service information available for selected device", "Error", wx.ICON_ERROR)
        else:
            wx.MessageBox("Please select a device to update",
                          "Error", wx.ICON_ERROR)
    def on_click_identify(self, event):
        selected_index = self.device_list.GetFirstSelected()
        if selected_index != -1:
            service_name = self.device_list.GetItemText(selected_index, 0)
            info = self.listener.services.get(service_name)
            if info:
                address = info.parsed_addresses(
                )[0] if info.parsed_addresses() else "N/A"
                port = info.port
                self.api_handler.identify_btclock(address)
            else:
                wx.MessageBox(
                    "No service information available for selected device", "Error", wx.ICON_ERROR)
        else:
            wx.MessageBox(
                "Please select a device to make an API call", "Error", wx.ICON_ERROR)
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
