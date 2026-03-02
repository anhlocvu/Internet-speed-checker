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

# Import our new lightweight engine
from . import speed_engine

addonHandler.initTranslation()

class SpeedResultsDialog(wx.Dialog):
    def __init__(self, parent, results_text):
        super(SpeedResultsDialog, self).__init__(parent, title=_("Internet Speed Test Results"))
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        # Results text in a read-only edit box
        # We ensure this box gets focus so the user can read results immediately
        self.resultsEdit = wx.TextCtrl(self, value=results_text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        mainSizer.Add(self.resultsEdit, 1, wx.EXPAND | wx.ALL, 10)
        
        # Close button
        buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.closeButton = wx.Button(self, wx.ID_CLOSE, label=_("&Close"))
        self.closeButton.Bind(wx.EVT_BUTTON, self.onClose)
        buttonsSizer.Add(self.closeButton, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        mainSizer.Add(buttonsSizer, 0, wx.ALIGN_CENTER)
        
        self.SetSizer(mainSizer)
        self.SetMinSize((500, 400))
        self.Layout()
        self.Centre()
        
        # Focus the results edit box by default instead of the close button
        self.resultsEdit.SetFocus()

    def onClose(self, event):
        self.Destroy()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    
    scriptCategory = _("Internet Speed Checker")

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        self._is_checking = False

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
        
        # Start the looping beep in a separate thread
        threading.Thread(target=self._beep_loop).start()
        
        # Run speed test in a separate thread
        threading.Thread(target=self._run_speed_test).start()

    def _beep_loop(self):
        """Plays a medium pitch beep every 0.7s while checking."""
        while self._is_checking:
            tones.beep(500, 50) # 500Hz, 50ms
            time.sleep(0.7)

    def _run_speed_test(self):
        try:
            # Using our lightweight engine
            results = speed_engine.get_speed_results()
            
            # Formatting results
            formatted_results = (
                "--- Internet Speed Test Report ---\n\n"
                f"Download Speed: {results.get('download', 0.0):.2f} Mbps\n"
                f"Upload Speed: {results.get('upload', 0.0):.2f} Mbps\n"
                f"Ping: {results.get('ping', 'N/A')} ms\n\n"
                f"Location: {results.get('location', 'Unknown')}\n"
                f"ISP: {results.get('isp', 'Unknown')}\n"
                f"Client IP: {results.get('ip', 'Unknown')}\n\n"
                "------------------------------------"
            )
            
            # Stop the beep loop before final success sound
            self._is_checking = False
            
            # Final success beep: high and long
            tones.beep(1000, 500) # 1000Hz, 500ms
            
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
        dlg.Show()
        gui.mainFrame.postPopup()
