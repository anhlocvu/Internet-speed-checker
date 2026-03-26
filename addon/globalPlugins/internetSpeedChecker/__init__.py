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
from gui.settingsDialogs import SettingsPanel, NVDASettingsDialog

# Import our engine and config
from . import speed_engine
from .config import conf

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
            ui.message("The result has been copied to the clipboard")
        except Exception as e:
            log.error(f"Internet Speed Checker copy error: {e}")
            ui.message(_("Error copying to clipboard."))
            if wx.TheClipboard.IsOpened():
                wx.TheClipboard.Close()

    def onClose(self, event):
        self.EndModal(wx.ID_CLOSE)

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    
    scriptCategory = _("Internet Speed Checker")

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        if SpeedCheckerSettingsPanel not in NVDASettingsDialog.categoryClasses:
            NVDASettingsDialog.categoryClasses.append(SpeedCheckerSettingsPanel)
        self._is_checking = False

    def terminate(self):
        try:
            NVDASettingsDialog.categoryClasses.remove(SpeedCheckerSettingsPanel)
        except:
            pass

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
            
            # Formatting results
            formatted_results = (
                "--- Internet Speed Test Report ---\n\n"
                f"Download Speed: {dl_val:.2f} {unit}\n"
                f"Upload Speed: {ul_val:.2f} {unit}\n"
                f"Ping: {results.get('ping', 'N/A')} ms\n\n"
                f"Location: {results.get('location', 'Unknown')}\n"
                f"ISP: {results.get('isp', 'Unknown')}\n"
                f"Client IP: {results.get('ip', 'Unknown')}\n\n"
                "------------------------------------"
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
