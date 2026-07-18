# Internet Speed Checker for NVDA
# Author: Lc_Boy
# License: GPL v2

import threading
import wx
import gui
from scriptHandler import script
import globalPluginHandler
import ui
from logHandler import log
import addonHandler
import os
import sys
import tones
import time
import api
from gui.settingsDialogs import SettingsPanel

# Import our engine, config and history
from . import speed_engine
from .config import conf
from . import history

addonHandler.initTranslation()

class SpeedCheckerSettingsPanel(SettingsPanel):
    title = _("Internet Speed Checker")

    def makeSettings(self, sizer):
        helper = gui.guiHelper.BoxSizerHelper(self, sizer=sizer)
        
        # Unit selection
        self.unitChoice = helper.addLabeledControl(
            _("&Speed unit:"),
            wx.Choice,
            choices=[_("Megabit (Mbps)"), _("Megabyte (MB/s)")]
        )
        current_unit = conf.unit
        self.unitChoice.SetSelection(0 if current_unit == "Mbps" else 1)

    def onSave(self):
        new_unit = "Mbps" if self.unitChoice.GetSelection() == 0 else "MB/s"
        conf.unit = new_unit

class SpeedResultsDialog(wx.Dialog):
    def __init__(self, parent, results_text):
        super(SpeedResultsDialog, self).__init__(parent, title=_("Internet Speed Test Results"))
        self.results_text = results_text
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        # Results text in a read-only edit box
        self.resultsEdit = wx.TextCtrl(self, value=results_text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        mainSizer.Add(self.resultsEdit, 1, wx.EXPAND | wx.ALL, 10)
        
        # Buttons Sizer
        buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Copy button
        self.copyButton = wx.Button(self, label=_("&Copy Results"))
        self.Bind(wx.EVT_BUTTON, self.onCopy, self.copyButton)
        buttonsSizer.Add(self.copyButton, 0, wx.ALL, 5)
        
        # Close button
        self.closeButton = wx.Button(self, wx.ID_CLOSE, label=_("&Close"))
        self.Bind(wx.EVT_BUTTON, self.onClose, self.closeButton)
        buttonsSizer.Add(self.closeButton, 0, wx.ALL, 5)
        
        mainSizer.Add(buttonsSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        self.SetSizer(mainSizer)
        self.SetMinSize((500, 400))
        self.Layout()
        self.Centre()
        
        # Set focus to results
        self.resultsEdit.SetFocus()

    def onCopy(self, event):
        # Using wx.TheClipboard for maximum reliability
        if not wx.TheClipboard.Open():
            ui.message(_("Failed to open clipboard."))
            return
            
        try:
            data = wx.TextDataObject()
            data.SetText(self.results_text)
            wx.TheClipboard.SetData(data)
            wx.TheClipboard.Close()
            
            # Announce the specific English phrase as requested
            ui.message(_("The result has been copied to the clipboard"))
        except Exception as e:
            log.error(f"Internet Speed Checker copy error: {e}")
            ui.message(_("Error copying to clipboard."))
            if wx.TheClipboard.IsOpened():
                wx.TheClipboard.Close()

    def onClose(self, event):
        self.EndModal(wx.ID_CLOSE)

class SpeedHistoryDetailDialog(wx.Dialog):
    def __init__(self, parent, entry):
        super(SpeedHistoryDetailDialog, self).__init__(parent, title=_("Internet Speed Test Details"))
        self.entry = entry
        
        dl_val = entry.get('download', 0.0)
        ul_val = entry.get('upload', 0.0)
        unit = entry.get('unit', 'Mbps')
        ping = entry.get('ping', 'N/A')
        isp = entry.get('isp', 'Unknown')
        loc = entry.get('location', 'Unknown')
        ip = entry.get('ip', 'Unknown')
        ts = entry.get('timestamp', 'Unknown')
        
        self.details_text = _(
            "--- Internet Speed Test Report ---\n\n"
            "Time: {ts}\n"
            "Download Speed: {dl_val:.2f} {unit}\n"
            "Upload Speed: {ul_val:.2f} {unit}\n"
            "Ping: {ping} ms\n\n"
            "Server: {loc}\n"
            "ISP: {isp}\n"
            "Client IP: {ip}\n\n"
            "------------------------------------"
        ).format(
            ts=ts, dl_val=dl_val, unit=unit, ul_val=ul_val, ping=ping, loc=loc, isp=isp, ip=ip
        )
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        self.detailsEdit = wx.TextCtrl(self, value=self.details_text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        mainSizer.Add(self.detailsEdit, 1, wx.EXPAND | wx.ALL, 10)
        
        buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Copy button
        self.copyButton = wx.Button(self, label=_("&Copy Details"))
        self.Bind(wx.EVT_BUTTON, self.onCopy, self.copyButton)
        buttonsSizer.Add(self.copyButton, 0, wx.ALL, 5)
        
        # Go back button (ID_CANCEL maps to Escape key automatically)
        self.backButton = wx.Button(self, wx.ID_CANCEL, label=_("&Go Back"))
        buttonsSizer.Add(self.backButton, 0, wx.ALL, 5)
        
        mainSizer.Add(buttonsSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        self.SetSizer(mainSizer)
        self.SetMinSize((500, 400))
        self.Layout()
        self.Centre()
        
        self.detailsEdit.SetFocus()

    def onCopy(self, event):
        if not wx.TheClipboard.Open():
            ui.message(_("Failed to open clipboard."))
            return
        try:
            data = wx.TextDataObject()
            data.SetText(self.details_text)
            wx.TheClipboard.SetData(data)
            wx.TheClipboard.Close()
            ui.message(_("The result has been copied to the clipboard"))
        except Exception as e:
            log.error(f"Internet Speed Checker history details copy error: {e}")
            ui.message(_("Error copying to clipboard."))
            if wx.TheClipboard.IsOpened():
                wx.TheClipboard.Close()

class SpeedHistoryDialog(wx.Dialog):
    def __init__(self, parent):
        super(SpeedHistoryDialog, self).__init__(parent, title=_("Internet Speed Checker History"))
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        self.historyList = wx.ListBox(self, style=wx.LB_SINGLE)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.onOpen, self.historyList)
        self.historyList.Bind(wx.EVT_CHAR_HOOK, self.onListChar)
        mainSizer.Add(self.historyList, 1, wx.EXPAND | wx.ALL, 10)
        
        buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.openButton = wx.Button(self, label=_("&Open"))
        self.Bind(wx.EVT_BUTTON, self.onOpen, self.openButton)
        buttonsSizer.Add(self.openButton, 0, wx.ALL, 5)
        
        self.deleteAllButton = wx.Button(self, label=_("&Delete All History"))
        self.Bind(wx.EVT_BUTTON, self.onDeleteAll, self.deleteAllButton)
        buttonsSizer.Add(self.deleteAllButton, 0, wx.ALL, 5)
        
        # Close button (ID_CANCEL maps to Escape key)
        self.closeButton = wx.Button(self, wx.ID_CANCEL, label=_("&Close"))
        buttonsSizer.Add(self.closeButton, 0, wx.ALL, 5)
        
        mainSizer.Add(buttonsSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        self.SetSizer(mainSizer)
        self.SetMinSize((600, 400))
        self.Layout()
        self.Centre()
        
        self.loadHistoryData()
        self.historyList.SetFocus()

    def loadHistoryData(self):
        self.history_items = history.load_history()
        self.historyList.Clear()
        
        if not self.history_items:
            self.historyList.Append(_("No history, all check history will be saved here."))
            self.openButton.Disable()
            self.deleteAllButton.Disable()
        else:
            self.openButton.Enable()
            self.deleteAllButton.Enable()
            for entry in self.history_items:
                display_str = _("Checked at: {timestamp}").format(
                    timestamp=entry.get('timestamp', '')
                )
                self.historyList.Append(display_str)
            self.historyList.SetSelection(0)

    def onOpen(self, event):
        selection = self.historyList.GetSelection()
        if selection == wx.NOT_FOUND or not self.history_items:
            return
            
        entry = self.history_items[selection]
        dlg = SpeedHistoryDetailDialog(self, entry)
        dlg.ShowModal()
        dlg.Destroy()
        self.historyList.SetFocus()

    def onListChar(self, event):
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_RETURN:
            self.onOpen(None)
        else:
            event.Skip()

    def onDeleteAll(self, event):
        history.clear_history()
        self.loadHistoryData()
        ui.message(_("All history has been deleted."))
        self.historyList.SetFocus()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    
    scriptCategory = _("Internet Speed Checker")

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        try:
            from gui.settingsDialogs import NVDASettingsDialog
            if SpeedCheckerSettingsPanel not in NVDASettingsDialog.categoryClasses:
                NVDASettingsDialog.categoryClasses.append(SpeedCheckerSettingsPanel)
        except Exception as e:
            log.error(f"Internet Speed Checker: Error registering settings panel: {e}")
        self._is_checking = False
        
        # Add menu item to NVDA's Tools menu
        self.menuItem = None
        wx.CallAfter(self.addMenuItem)

    def terminate(self):
        try:
            from gui.settingsDialogs import NVDASettingsDialog
            NVDASettingsDialog.categoryClasses.remove(SpeedCheckerSettingsPanel)
        except Exception as e:
            log.error(f"Internet Speed Checker: Error unregistering settings panel: {e}")
            
        # Remove menu item from Tools menu
        if self.menuItem:
            try:
                mainFrame = gui.mainFrame
                if mainFrame and hasattr(mainFrame, "sysTrayIcon"):
                    mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self.menuItem)
                    if hasattr(mainFrame.sysTrayIcon, "toolsMenu"):
                        mainFrame.sysTrayIcon.toolsMenu.Remove(self.menuItem.GetId())
            except Exception as e:
                log.error(f"Internet Speed Checker: Error removing menu item: {e}")

    def addMenuItem(self):
        try:
            mainFrame = gui.mainFrame
            if not mainFrame or not hasattr(mainFrame, "sysTrayIcon"):
                return
            
            # Locate the Tools menu in an NVDA version-agnostic way
            toolsMenu = None
            if hasattr(mainFrame.sysTrayIcon, "toolsMenu"):
                toolsMenu = mainFrame.sysTrayIcon.toolsMenu
            else:
                # Fallback logic to traverse tray menu items
                trayMenu = getattr(mainFrame.sysTrayIcon, "menu", None)
                if trayMenu:
                    for item in trayMenu.GetMenuItems():
                        if item.GetSubMenu() and item.GetItemLabelText() == _("Tools"):
                            toolsMenu = item.GetSubMenu()
                            break
            
            if toolsMenu:
                # Append menu item
                self.menuItem = toolsMenu.Append(
                    wx.ID_ANY,
                    _("Internet Speed Checker &History..."),
                    _("View the history of internet speed tests.")
                )
                # Bind the menu event directly to the sysTrayIcon which triggers it
                mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onHistoryMenu, self.menuItem)
        except Exception as e:
            log.error(f"Internet Speed Checker: Error adding menu item: {e}")

    def onHistoryMenu(self, event):
        self._show_history()

    def _show_history(self):
        gui.mainFrame.prePopup()
        dlg = SpeedHistoryDialog(gui.mainFrame)
        dlg.ShowModal()
        dlg.Destroy()
        gui.mainFrame.postPopup()

    @script(
        description=_("Checks the current internet speed."),
        gestures=["kb:control+shift+nvda+i"]
    )
    def script_checkSpeed(self, gesture):
        if self._is_checking:
            ui.message(_("Internet speed check is already in progress."))
            return
        
        ui.message(_("Internet speed checking..."))
        self._is_checking = True
        threading.Thread(target=self._beep_loop).start()
        threading.Thread(target=self._run_speed_test).start()

    @script(
        description=_("Opens the internet speed check history."),
        gestures=["kb:control+shift+nvda+h"]
    )
    def script_showHistory(self, gesture):
        wx.CallAfter(self._show_history)

    def _beep_loop(self):
        while self._is_checking:
            tones.beep(500, 50)
            time.sleep(0.7)

    def _run_speed_test(self):
        try:
            results = speed_engine.get_speed_results()
            
            # Unit conversion
            unit = conf.unit
            dl_val = results.get('download', 0.0)
            ul_val = results.get('upload', 0.0)
            
            if unit == "MB/s":
                dl_val = dl_val / 8
                ul_val = ul_val / 8
            
            # Save to history
            history.add_history_entry(
                download=round(dl_val, 2),
                upload=round(ul_val, 2),
                ping=results.get('ping', 'N/A'),
                unit=unit,
                isp=results.get('isp', 'Unknown'),
                location=results.get('location', 'Unknown'),
                ip=results.get('ip', 'Unknown')
            )
            
            # Formatting results
            formatted_results = _(
                "--- Internet Speed Test Report ---\n\n"
                "Download Speed: {dl_val:.2f} {unit}\n"
                "Upload Speed: {ul_val:.2f} {unit}\n"
                "Ping: {ping} ms\n\n"
                "Server: {loc}\n"
                "ISP: {isp}\n"
                "Client IP: {ip}\n\n"
                "------------------------------------"
            ).format(
                dl_val=dl_val, unit=unit, ul_val=ul_val, ping=results.get('ping', 'N/A'),
                loc=results.get('location', 'Unknown'), isp=results.get('isp', 'Unknown'),
                ip=results.get('ip', 'Unknown')
            )
            
            self._is_checking = False
            tones.beep(1000, 500)
            wx.CallAfter(self._show_results, formatted_results)
            
        except Exception as e:
            self._is_checking = False
            log.error(f"Internet Speed Checker error: {e}")
            error_msg = _("Error occurred while checking internet speed: {error}").format(error=str(e))
            wx.CallAfter(ui.message, error_msg)
        finally:
            self._is_checking = False

    def _show_results(self, results):
        gui.mainFrame.prePopup()
        dlg = SpeedResultsDialog(gui.mainFrame, results)
        dlg.ShowModal()
        dlg.Destroy()
        gui.mainFrame.postPopup()
