#! /usr/bin/env python
#
#  Copyright  2019 Henning Follmann <hfollmann@itcfollmann.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""MCA application: GUI for MCA data aquisition"""

import wx
import sys
import os
import mca8000d
import numpy
import matplotlib

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas


class Instrument():
        def __init__(self):
                self.device = mca8000d.device()
       
                        
                

        def bRunning(self):
                
                status = self.device.reqStatus()
                return (status.MCA_EN)


        def start(self):
                self.device.enable_MCA_MCS()

        def stop(self):
                self.device.disable_MCA_MCS()

        def getAcquisitionTime(self):
                status = self.device.reqStatus()
                time = status.RealTime/1000
                return(time)
        
        def getSpectrum(self):
                res = self.device.spectrum(False, False)
                return (res[0])

        def save(self, filename):
                spectrum = self.getSpectrum()
                mca8000d.saveSpectrum(filename, spectrum)
                

        def clear(self):
                self.device.spectrum(True, True)


        def loadConfig(self, filename):
                newCfg=mca8000d.readConfig(filename)
                newCfgString = mca8000d.createCfgString(newCfg)
                self.device.sendCmdConfig(newCfgString)
                

        
                
                
                
class StatusPanel(wx.Panel):

        def __init__(self, parent):
                wx.Panel.__init__(self, parent,-1)
                self.statusLabel= wx.StaticText(self, -1, "Acquisition:")
                self.statusValue= wx.TextCtrl(self,-1,style=wx.TE_READONLY)
                self.timeLabel= wx.StaticText(self, -1, "Time:")
                self.timeValue= wx.TextCtrl(self,-1,style=wx.TE_READONLY)
                self.sizer = wx.FlexGridSizer(cols=2, hgap=6, vgap=6)
                self.sizer.AddMany([self.statusLabel, self.statusValue, self.timeLabel, self.timeValue])
                self.SetSizer(self.sizer)

        def setStatus(self, bRunning):
                statusValue=""
                if bRunning:
                        statusValue = "running"
                else:
                        statusValue = "stopped"
                self.statusValue.SetValue(statusValue)
                return True

        def setTimeValue(self, time):
                timeValue = str(time)
                self.timeValue.SetValue(timeValue)
                return True
        

class MatplotPanel(wx.Panel):
        
        def __init__(self, parent):
                wx.Panel.__init__(self, parent,-1, style=wx.SUNKEN_BORDER)

                self.sizer = wx.BoxSizer(wx.VERTICAL)
                self.SetSizer(self.sizer)
                self.figure = Figure()
                self.axes = self.figure.add_subplot(1,1,1)
                self.canvas = FigureCanvas(self, -1, self.figure)
                self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)

        def plotSpectrum(self, spectrum):
                
                nChannels = len(spectrum);
                c = numpy.arange(0, nChannels, 1)
                self.axes.clear()
                self.axes.plot(c, spectrum, 'k,')
                self.canvas.draw()



class Frame (wx.Frame):
        def __init__(self, parent, title):
                self.instrument = Instrument()
                # reload custom config
                self.instrument.loadConfig("mca8000d.cfg")
                wx.Frame.__init__(self,parent,title=title,pos=wx.DefaultPosition,size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE)
                self.menuBar = wx.MenuBar()
                self.menuFile = wx.Menu()
                e_xit=self.menuFile.Append(-1, "Exit", "Exit program")
                s_ave=self.menuFile.Append(-1, "Save", "Save spectrum file")
                self.Bind(wx.EVT_MENU, self.onExit, e_xit)
                self.Bind(wx.EVT_MENU, self.onSave, s_ave)
                self.menuBar.Append(self.menuFile, "File")
                self.menuSpectrum = wx.Menu()
                self.menuBar.Append(self.menuSpectrum, "Spectrum")
                s_tart=self.menuSpectrum.Append(-1, "Start", "Start data acquisition")
                s_top=self.menuSpectrum.Append(-1, "Stop", "Stop data acquisition")
                c_lear=self.menuSpectrum.Append(-1, "Clear", "Clear data")
                self.Bind(wx.EVT_MENU, self.onStart, s_tart)
                self.Bind(wx.EVT_MENU, self.onStop, s_top)
                self.Bind(wx.EVT_MENU, self.onClear, c_lear)
                self.SetMenuBar(self.menuBar)
                self.sp = wx.SplitterWindow(self, -1)
                self.m = MatplotPanel(self.sp)
                self.s = StatusPanel(self.sp)
                self.sp.SplitVertically(self.m,self.s, -100)
                self.Bind(wx.EVT_CLOSE, self.onClose)
                self.updateTimer=wx.Timer(self)
                self.Bind(wx.EVT_TIMER, self.onUpdateTimer, self.updateTimer)
                self.updateTimer.Start(milliseconds=2000, oneShot=False)

        def onExit(self, event):
                self.Close(True)

        def onClose(self, event):
                
                self.instrument.stop()
                self.instrument.clear()
                self.Destroy()
                
        def onUpdateTimer(self, event):
                self.update()

        def onSave(self, event):
                wildcard = '*'
                dialog = wx.FileDialog(None, "Save Spectrum", os.getcwd(),"", wildcard, wx.SAVE|wx.OVERWRITE_PROMPT)
                if dialog.ShowModal() == wx.ID_OK:
                        filename = dialog.GetPath()
                        self.instrument.save(filename)
                dialog.Destroy()

        def onStart(self, event):
                self.instrument.start()
                self.update()


        def onStop(self, event):
                self.instrument.stop()
                self.update()
                

        def onClear(self, event):
                self.instrument.clear()
                self.update()
        

        def update(self):
                self.s.setStatus(self.instrument.bRunning())
                self.s.setTimeValue(self.instrument.getAcquisitionTime())
                spectrum = self.instrument.getSpectrum()
                self.m.plotSpectrum(spectrum)
                

class MCAApp(wx.App):
        def OnInit(self):
                
                self.frame = Frame(parent=None, title='MCA')
                self.frame.Show()
                self.SetTopWindow(self.frame)
                self.frame.update()
                return True

    
def main():
        app = MCAApp()
        app.MainLoop()

    
if __name__ == '__main__':
    
        main()
