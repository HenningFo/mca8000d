#! /usr/bin/env python
#
#  Copyright 2019 Henning Follmann <hfollmann@itcfollmann.com>
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

"""A USB interface to AMPTEK's MCA8000d"""
   

import usb.core
import usb.util
import struct
import sys
import time

def chksum(data):
    checksum = 0;
    for b in bytearray(data):
        checksum += int(b)
    return (((checksum & 0xffff) ^ 0xffff) + 1)


# pack and unpack integer
# device expects big endian
def packint(unsint):
    """convert integer to 2 bytes (big endian)"""
    ba = struct.pack('>H', unsint)
    return (ba)

def unpackint(twobytes):
    """convert two bytes to integer (from big endian)"""
    res = struct.unpack('>H',twobytes)
    return (res[0])

# unpack status fields
# here it is little endian
def fourbytes2float(ba):
    """convert four bytes to float"""
    nums = struct.unpack('<I', ba)
    return (1.0 * nums[0])

def fourbytes2long(ba):
    """convert four bytes to integer"""
    nums = struct.unpack('<I', ba)
    return nums[0]

def threebytes2long(ba):
    """convert three bytes to integer"""
    num = int(ba[0]) + (int(ba[1]) * 256) + (int(ba[2]) * 65536)
    return num



# pack message
# message format:
# msg[0] = header[0] # this is sync1
# msg[1] = header[1] #         sync2
# msg[2] = header[2] #         requestid1
# msg[3] = header[3] #         requestid2
# msg[4] = high byte len(data)
# msg[5] = low byte len(data)
# msg[6] = data[0]
# ...
# msg[len(data)+5]
# msg[len(data)+6]=high byte checksum # msg[-2]
# msg[len(data)+7]=low byte checksum  # msg[-1]
def packmsg(header, data):
    """packmsg prepares a msg to send it to the device"""
    length = len(data)
    ba = header + packint(length) + data
    cs = chksum(ba)
    return (ba + packint(cs))


class status:
    """status of a mca8000d device"""
    def __init__(self, raw):
        """parse mca8000d status msg into status class"""
        self.DEVICE_ID = raw[39]
        self.FastCount= fourbytes2long(raw[0:4])
        self.SlowCount= fourbytes2long(raw[4:8])
        self.GP_COUNTER= fourbytes2long(raw[8:12])
        self.AccumulationTime = int(raw[12]) + (threebytes2long(raw[13:16]) * 100)  # in msec
        self.RealTime = fourbytes2long(raw[20:24]) # in msec
        self.Firmware=raw[24]
        self.FPGA=raw[25]
        if self.Firmware > 0x65 :
            self.Build = raw[37] & 0xF
        else:
            self.Build = 0
        self.bDMCA_LiveTime =  (self.DEVICE_ID == 3) and (self.Firmware >= 0x67)
        if self.bDMCA_LiveTime:
            self.LiveTime = fourbytes2long(raw[16:20]) # in msec
        else:
            self.LiveTime = 0
        if raw[29] < 128:
            self.SerialNumber = fourbytes2long(raw[26:30])
        else:
            self.SerialNumber = -1
        self.PresetRtDone = (raw[35] & 128) == 128
        self.PresetLtDone = False
        self.AFAST_LOCKED = False
        if self.bDMCA_LiveTime :
            self.PresetLtDone = (raw[35] & 64) == 64
        else:
            self.AFAST_LOCKED = (raw[35] & 64) == 64
        self.MCA_EN = (raw[35] & 32) == 32
        self.PRECNT_REACHED = (raw[35] & 16) == 16
        self.SCOPE_DR = (raw[35] & 4) == 4
        self.DP5_CONFIGURED = (raw[35] & 2) == 2
        self.AOFFSET_LOCKED = (raw[36] & 128) == 128
        self.MCS_DONE = (raw[36] & 64) == 64
        self.b80MHzMode = (raw[36] & 2) == 2
        self.bFPGAAutoClock = (raw[36] & 1) == 1
        self.PC5_PRESENT = (raw[38] & 128) == 128
        if self.PC5_PRESENT:
            self.PC5_HV_POL = (raw[38] & 64) == 64
            self.PC5_8_5V = (raw[38] & 32) == 32
        else:
            self.PC5_HV_POL = False
            self.PC5_8_5V = False
        self.DPP_ECO = raw[49]

        

def printStatus(status):
    sys.stdout.write('================ MCA8000D status ===================\n')
    sys.stdout.write('Device Id       : ' + str(status.DEVICE_ID) +'\n')
    sys.stdout.write('Firmware        : ' + str(status.Firmware) +'\n')
    sys.stdout.write('FPGA            : ' + str(status.FPGA) +'\n')
    sys.stdout.write('SerialNumber    : ' + str(status.SerialNumber) +'\n')
    sys.stdout.write('AccumulationTime: ' + str(status.AccumulationTime) +' msec\n')        
    sys.stdout.write('RealTime        : ' + str(status.RealTime) +' msec\n')
    sys.stdout.write('FastCount       : ' + str(status.FastCount) +'\n')
    sys.stdout.write('SlowCount       : ' + str(status.SlowCount) +'\n')
    sys.stdout.write('GP Counter      : ' + str(status.GP_COUNTER) +'\n')
    sys.stdout.write('MCA_EN          : ' )
    if status.MCA_EN:
        sys.stdout.write('Yes\n')
    else:
        sys.stdout.write('No\n')
    sys.stdout.write('MCS_DONE        : ' )
    if status.MCS_DONE:
        sys.stdout.write('Yes\n')
    else:
        sys.stdout.write('No\n')
    sys.stdout.write('PRECNT_REACHED  : ' )
    if status.PRECNT_REACHED:
        sys.stdout.write('Yes\n')
    else:
        sys.stdout.write('No\n')
    sys.stdout.write('PC5_PRESENT     : ' )
    if status.PC5_PRESENT:
        sys.stdout.write('Yes\n')
    else:
        sys.stdout.write('No\n')
    sys.stdout.write('DPP_ECO         : ' + str(status.DPP_ECO) +'\n')
    sys.stdout.write('====================================================\n')
        

#############################################################################
# mca8000d config
configParameters = {"RESC" : "Reset Configuration",\
                    "PURE" : "PUR Interval on/off",\
                    "MCAS" : "MCA Source",\
                    "MCAC" : "MCA/MCS Channels",\
                    "SOFF" : "Set Spectrum Offset",\
                    "GAIA" : "Analog Gain Index",\
                    "PDMD" : "Peak Detect Mode (min/max)",\
                    "THSL" : "Slow Threshold",\
                    "TLLD" : "LLD Threshold",\
                    "GATE" : "Gate Control",\
                    "AUO1" : "AUX OUT Selection",\
                    "PRER" : "Preset Real Time",\
                    "PREL" : "Preset Life Time",\
                    "PREC" : "Preset Counts",\
                    "PRCL" : "Preset Counts Low Threshold",\
                    "PRCH" : "Preset Counts High Threshold",\
                    "SCOE" : "Scope Trigger Edge",\
                    "SCOT" : "Scope Trigger Position",\
                    "SCOG" : "Digital Scope Gain",\
                    "MCSL" : "MCS Low Threshold",\
                    "MCSH" : "MCS High Threshold",\
                    "MCST" : "MCS Timebase",\
                    "AUO2" : "AUX OUT 2 Selection",\
                    "GPED" : "G.P.Counter Edge",\
                    "GPIN" : "G.P. Counter Input",\
                    "GPME" : "G.P. Counter Uses MCA_EN",\
                    "GPGA" : "G.P. Counter Uses Gate",\
                    "GPMC" : "G.P. Counter Cleared With MCA",\
                    "MCAE" : "MCA/MCS Enable"}



def printConfig(cfg):
    sys.stdout.write('================ MCA8000D CFG ===================\n')
    for k in cfg.keys():
        sys.stdout.write(configParameters[k] + ' : ' + cfg[k] +'\n')
    sys.stdout.write('============================= ===================\n')




spectrumSize ={ 1 : 255,\
                2 : 255,\
                3 : 511,\
                4 : 511,\
                5 : 1023,\
                6 : 1023,\
                7 : 2047,\
                8 : 2047,\
                9 : 4095,\
                10 : 4095,\
                11 : 8191,\
                12 : 8191}  # max channel number zero indexed

    
class device:
    """device provides all communications to a mca8000d device"""
    def __init__(self):
        self.dev=usb.core.find(idVendor=0x10c4, idProduct=0x842a)
        if self.dev is None:
            raise ValueError('Device not found')

            
        self.dev.set_configuration()
        # cfg=self.dev.get_active_configuration()
        # intf=cfg[(0,0)]
        # ep_out=usb.util.find_descriptor(
        #    intf,
        #    # match the first OUT endpoint
        #    custom_match = \
        #    lambda e: \
        #    usb.util.endpoint_direction(e.bEndpointAddress) == \
        #    usb.util.ENDPOINT_OUT)
        # self.eout=ep_out.bEndpointAddress
        # ep_in=usb.util.find_descriptor(
        #     intf,
        #     # match the first IN endpoint
        #     custom_match = \
        #     lambda e: \
        #     usb.util.endpoint_direction(e.bEndpointAddress) == \
        #     usb.util.ENDPOINT_IN)
        # self.ein=ep_in.bEndpointAddress
        self.eout=2
        self.ein=129
        self.timeout=500

    def __del__(self):
        self.dev.reset()
        usb.util.dispose_resources(self.dev)

    def sendCmd(self, req_pid1, req_pid2, data):
        """sends raw cmd over usb"""
        header = bytearray(4)
        header[0]=0xF5        # SYNC1
        header[1]=0xFA        # SYNC2
        header[2]=req_pid1
        header[3]=req_pid2
        pout = packmsg(header, data)
        # send to device
        res=self.dev.write(self.eout, pout, self.timeout)
        return res
    
        
    def recvCmd(self):
        """receives raw cmd over usb"""
        devmsg = self.dev.read(self.ein, 65535, self.timeout)
        chksm = unpackint(devmsg[-2:])
        cntrl = chksum(devmsg[:-2])
        assert chksm == cntrl
        return ((devmsg[2], devmsg[3], devmsg[6:-2]))

    def reqStatus(self):
        """get status of  mca8000d device"""
        data=''
        self.sendCmd(1,1,data)
        statusmsg = self.recvCmd()
        return (status(statusmsg[2]))
    
    def reqHWConfig(self):
        """get hardware configuration from device"""
        data=''
        for confp in configParameters.keys():
            data += confp + '=?;'
        # pid1 = 0x20
        # pid2 = 0x03
        self.sendCmd(0x20,0x03,data)
        cfgmsg = self.recvCmd()
        l = len(cfgmsg[2])
        fmt = str(l) + 's'
        lcfgstr = struct.unpack(fmt, cfgmsg[2])
        cfg = {}
        for param in lcfgstr[0].split(';'):
            pv = param.split('=')
            if len(pv) == 2:
                cfg.setdefault(pv[0], pv[1])
        return(cfg)

    def sendCmdConfig(self, cmd):
        """sends a configuration string to device"""
        # pid1 = 0x20
        # pid2 = 0x02
        self.sendCmd(0x20, 0x02, cmd)
        cfgmsg = self.recvCmd()
        return (cfgmsg)

    def setPresetTime(self, time):
        """set preset (real) time"""
        cmd = 'PRER='
        if (time < 0):
            raise ValueError('Negative time not allowed\n')
        if (time == 0):
            cmd = cmd + "OFF;"
        else:
            cmd = cmd + str(time) + ";"
        self.sendCmdConfig(cmd)
        
            


        
    # start MCA MCS scan
    def enable_MCA_MCS(self):
        """start data acquisition"""
        data = ''
        # pid1 = 0xF0
        # pid2 = 0x02
        self.sendCmd(0xF0, 0x02, data)
        res = self.recvCmd()
        return (res)

    # stop MCA MCS scan
    def disable_MCA_MCS(self):
        """stop data acquistion"""
        data = ''
        # pid1 = 0xF0
        # pid2 = 0x03
        self.sendCmd(0xF0, 0x03, data)
        res = self.recvCmd()
        return (res)

    def spectrum(self, bStatus, bClear):
        """get spectrum data 
           if bStatus is True it will get status too
           if bClear is True spectrum data (and status) will be cleared"""
        data = ''
        # pid1 = 0x02
        # pid2 = 0x01...0x04
        Pid2 = 0x01
        if bStatus:
            Pid2 += 2
        if bClear:
            Pid2 += 1
        self.sendCmd(0x02, Pid2, data)
        res = self.recvCmd()
        maxChan = spectrumSize[res[1]]
        spectrum = []
        sta = None
        for indx in range(0, maxChan*3, 3):
            spectrum.append( threebytes2long(res[2][indx:(indx+3)]) )
            
        if bStatus:
             sta = status(res[2][-64:])
        
        return ([spectrum, sta])


def saveSpectrum(filename, spectrum):
    """write spectrum to file, one channel per line"""
    fh = open(filename, "w")
    for chan in spectrum:
        fh.write("{}\n".format( str(chan)))
    fh.close()


def demo():
    """Example how to use"""
    sys.stdout.write('Find MCA8000D device\n')
    dev = device()
    status = dev.reqStatus()
    printStatus(status)
    # if still running
    if status.MCA_EN :
        sys.stdout.write('MCA8000D currently running... stopping now\n')
        dev.disable_MCA_MCS()
    sys.stdout.write('MCA8000D clearing\n')
    dev.spectrum(True, True)
    sys.stdout.write('Setting preset time to 20\n')
    dev.setPresetTime(20)
    sys.stdout.write('MCA8000D start scan\n')
    dev.enable_MCA_MCS()
    status=dev.reqStatus()
    sys.stdout.write('\tscanning\n')
    while ((status.RealTime/1000)<20 ):
        time.sleep(1)
        sys.stdout.write('\t.\n')
        status=dev.reqStatus()
        
    sys.stdout.write(' done\n')
    dev.disable_MCA_MCS()
    sys.stdout.write('safe spectrum to demo.dat\n')
    spec=dev.spectrum(True, True)
    saveSpectrum('demo.dat', spec[0])
    dev.setPresetTime(0)
    config=dev.reqHWConfig()
    printConfig(config)
    dev=None
    #done



    
if __name__ == '__main__':

    demo()

    
 
