import wx
import wx.lib.mixins.listctrl


class DevicesPanel(wx.ListCtrl, wx.lib.mixins.listctrl.ColumnSorterMixin,    wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin,
                   ):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        self.column_headings = [
            "Hostname", "Version", "FW commit", "HW Revision", "IP", "WebUI commit"]
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
