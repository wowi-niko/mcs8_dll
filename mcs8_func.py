import tkinter as tk
from tkinter import ttk
import ctypes
from ctypes import c_int, POINTER, byref
from structures import *

# Add this tooltip class at the top of the file
class CreateToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def showtip(self):
        if self.tw:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack()

    def hidetip(self):
        if self.tw:
            self.tw.destroy()
            self.tw = None



# --- MCS8 Wrapper Class ---
class MCS8:
    """
    A wrapper class for interfacing with the dmcs8.dll.
    
    Note:
      The device provides its settings via functions like GetSettingData, GetDatSetting,
      and GetMCSSetting. To change settings (for example, the spectra length) you must use
      the built-in command interpreter by sending commands via RunCmd.
      
    Attributes:
      nDev (int): The device number.
      dll (WinDLL): The loaded dmcs8.dll.
    """
    # Class constants
    ST_RUNTIME   = 0
    ST_OFLS      = 1
    ST_TOTALSUM  = 2
    ST_ROISUM    = 3
    ST_ROIRATE   = 4
    ST_SWEEPS    = 5
    ST_STARTS    = 6
    ST_ZEROEVTS  = 7

    def __init__(self, device: int = 0, dll_path: str = "dmcs8.dll"):
        self.nDev = device
        self.dll = ctypes.WinDLL(dll_path)
        self._setup_dll()

    def _setup_dll(self) -> None:
        """Configure DLL function signatures."""
        self.dll.RunCmd.argtypes = [c_int, ctypes.c_char_p]
        self.dll.RunCmd.restype  = None

        self.dll.GetStatus.argtypes = [c_int]
        self.dll.GetStatus.restype  = c_int

        self.dll.GetStatusData.argtypes = [POINTER(ACQSTATUS), c_int]
        self.dll.GetStatusData.restype  = c_int

        self.dll.GetSettingData.argtypes = [POINTER(ACQSETTING), c_int]
        self.dll.GetSettingData.restype  = c_int

        self.dll.LVGetCnt.argtypes = [POINTER(c_double), c_int]
        self.dll.LVGetCnt.restype  = c_int

        self.dll.LVGetRoi.argtypes = [POINTER(c_int), c_int]
        self.dll.LVGetRoi.restype  = c_int

        self.dll.LVGetDat.argtypes = [POINTER(c_int), c_int]
        self.dll.LVGetDat.restype  = c_int

        self.dll.LVGetCDefData.argtypes = [POINTER(LVCOINCDEF)]
        self.dll.LVGetCDefData.restype  = c_int

        self.dll.GetMCSSetting.argtypes = [POINTER(BOARDSETTING), c_int]
        self.dll.GetMCSSetting.restype  = c_int

        self.dll.GetDatSetting.argtypes = [POINTER(DATSETTING)]
        self.dll.GetDatSetting.restype  = c_int

        self.dll.GetBlock.argtypes = [POINTER(c_int), c_int, c_int, c_int, c_int]
        self.dll.GetBlock.restype  = None

        self.dll.Start.argtypes = [c_int]
        self.dll.Start.restype  = None

        self.dll.Halt.argtypes = [c_int]
        self.dll.Halt.restype  = None

        self.dll.Continue.argtypes = [c_int]
        self.dll.Continue.restype  = None

        # New functions from the DLL header:
        self.dll.Erase.argtypes = [c_int]
        self.dll.Erase.restype  = None

        self.dll.SaveData.argtypes = [c_int, c_int]
        self.dll.SaveData.restype  = None

    def run_cmd(self, command: str) -> str:
        """Send a command string to the device and return the modified string."""
        # Create a mutable buffer with extra space for the result
        buffer_size = len(command) + 1024  # Command + space for sprintf result
        command_buffer = ctypes.create_string_buffer(command.encode('utf-8'), buffer_size)
        
        # Configure the DLL function signature
        self.dll.RunCmd.argtypes = [ctypes.c_int, ctypes.c_char_p]
        self.dll.RunCmd.restype = None
        
        # Call the function - it will modify command_buffer in-place
        self.dll.RunCmd(0, command_buffer)
        
        # Return the modified string
        return command_buffer.value.decode('utf-8')

    def start(self) -> None:
        """Start measurement."""
        self.dll.Start(self.nDev)
    
    def halt(self) -> None:
        """Stop measurement."""
        self.dll.Halt(self.nDev)
    
    def continue_device(self) -> None:
        """Continue measurement."""
        self.dll.Continue(self.nDev)

    def erase(self) -> None:
        """Erase spectrum."""
        self.dll.Erase(self.nDev)

    def save_data(self, all_val: int) -> None:
        """
        Save data.
        
        Args:
            all_val (int): Use 1 to save all data.
        """
        self.dll.SaveData(self.nDev, all_val)

    def set_mpaname(self, filename: str) -> None:
        """
        Set the MPA filename.
        
        This sends the command "mpaname=filename" to the device.
        """
        self.run_cmd(f"mpaname={filename}")

    def save_cnf(self) -> None:
        """Store the current settings to MCS8A.SET (save configuration)."""
        self.run_cmd("savecnf")

    def savempa(self) -> None:
        """Save configuration and spectra data (overwrite existing file)."""
        self.run_cmd("savempa")

    def get_status(self) -> ACQSTATUS:
        """
        Retrieve the current acquisition status.
        
        Returns:
            ACQSTATUS: Status information from the device.
        """
        self.dll.GetStatus(self.nDev)
        status = ACQSTATUS()
        self.dll.GetStatusData(byref(status), self.nDev)
        return status

    def get_acq_setting(self, channel_id=0) -> ACQSETTING:
        """
        Retrieve the acquisition settings from the device.
        
        Returns:
            ACQSETTING: The acquisition settings structure.
        """
        acq = ACQSETTING()
        self.dll.GetSettingData(byref(acq), channel_id)
        return acq

    def check_status(self):
        acq = ACQSETTING()
        return self.dll.GetSettingData(byref(acq), self.nDev)
    
    def get_dat_setting(self) -> DATSETTING:
        """
        Retrieve the data settings from the device.
        
        Returns:
            DATSETTING: The data settings structure.
        """
        dat = DATSETTING()
        self.dll.GetDatSetting(byref(dat))
        return dat

    def get_mcs_setting(self) -> BOARDSETTING:
        """
        Retrieve the board (MCS) settings from the device.
        
        Returns:
            BOARDSETTING: The board settings structure.
        """
        board = BOARDSETTING()
        self.dll.GetMCSSetting(byref(board), self.nDev)
        return board

    def get_lvcoincdef(self) -> LVCOINCDEF:
        """
        Retrieve the coincidence definition settings.
        
        Returns:
            LVCOINCDEF: The coincidence definition structure.
        """
        lcdef = LVCOINCDEF()
        self.dll.LVGetCDefData(byref(lcdef))
        return lcdef

    def get_block(self, start: int, end: int, step: int = 1, channel_id: int = 0) -> list:
        """
        Retrieve a block of data points.
        
        Args:
            start (int): Starting index.
            end (int): Ending index (non-inclusive).
            step (int, optional): Step size.
            channel_id (int, optional): Channel ID.
        
        Returns:
            list: A list of data points.
        """
        num_points = end - start
        block = (c_int * num_points)()
        self.dll.GetBlock(block, start, end, step, channel_id)
        return list(block)

    def set_range(self, new_range: int) -> None:
        """
        Change the spectra length (range) by sending a command to the server.
        
        The recommended method is to use the built-in command interpreter.
        For example, to set the range to 16384, the command "range=16384" is sent.
        
        Args:
            new_range (int): The new spectra length.
        """
        command = f"range={new_range}"
        self.run_cmd(command)

    def run_command_loop(self) -> None:
        """
        Run a command loop to interact with the device.
        
        This integrated routine handles user commands such as querying status,
        acquisition settings, board settings, data, and sending custom commands.
        """
        print("\nCommands: Q=Quit, H=Help, S=Status, T=AcqSetting, B=BoardSetting, D=Data, F=DatSetting")
        while True:
            command = input("Enter command: ").strip().upper()
            if command == "Q":
                break
            elif command == "H":
                print("Commands: Q=Quit, H=Help, S=Status, T=AcqSetting, B=BoardSetting, D=Data, F=DatSetting")
            elif command == "S":
                status = self.get_status()
                self.print_status(status)
            elif command == "T":
                acq = self.get_acq_setting()
                self.print_acq_setting(acq)
            elif command == "B":
                board = self.get_mcs_setting()
                self.print_mcs_setting(board)
            elif command == "D":
                block = self.get_block(0, 30)
                acq = self.get_acq_setting()
                print(f"First 30 datapoints (acq range: {acq.range}):")
                for pt in block:
                    print(pt)
            elif command == "F":
                dat = self.get_dat_setting()
                self.print_dat_setting(dat)
            else:
                self.run_cmd(command)

    @classmethod
    def print_status(cls, status: ACQSTATUS) -> None:
        print("Status:")
        print("  total =", status.cnt[cls.ST_TOTALSUM])
        print("  roi =", status.cnt[cls.ST_ROISUM])
        print("  rate =", status.cnt[cls.ST_ROIRATE])
        print("  ofls =", status.cnt[cls.ST_OFLS])

    @staticmethod
    def print_acq_setting(acq: ACQSETTING) -> None:
        print("Acquisition Settings:")
        print("  range =", acq.range)
        print("  cftfak =", acq.cftfak)
        print("  roimin =", acq.roimin)
        print("  roimax =", acq.roimax)
        print("  nregions =", acq.nregions)
        print("  caluse =", acq.caluse)
        print("  calpoints =", acq.calpoints)
        print("  active =", acq.active)
        print("  roipreset =", acq.eventpreset)

    @staticmethod
    def print_dat_setting(dat: DATSETTING) -> None:
        filename = dat.filename.decode("utf-8").rstrip("\x00")
        print("Data Settings:")
        print("  savedata =", dat.savedata)
        print("  autoinc =", dat.autoinc)
        print("  fmt =", dat.fmt)
        print("  mpafmt =", dat.mpafmt)
        print("  sephead =", dat.sephead)
        print("  filename =", filename)

    @staticmethod
    def print_mcs_setting(board: BOARDSETTING) -> None:
        print("Board Settings:")
        print("  sweepmode =", board.sweepmode)
        print("  prena =", board.prena)
        print("  cycles =", board.cycles)
        print("  sequences =", board.sequences)
        print("  digio =", board.digio)
        print("  digval =", board.digval)
        print("  dac0 =", board.dac0)
        print("  dac1 =", board.dac1)
        print("  dac2 =", board.dac2)
        print("  dac3 =", board.dac3)
        print("  dac4 =", board.dac4)
        print("  dac5 =", board.dac5)
        print("  serno =", board.serno)
        print("  ddruse =", board.ddruse)
        print("  active =", board.active)
        print("  holdafter =", board.holdafter)
        print("  swpreset =", board.swpreset)
        print("  fstchan =", board.fstchan)
        print("  timepreset =", board.timepreset)
    
    # --- Helper methods for display (returning text strings) ---
    @classmethod
    def status_text(cls, status: ACQSTATUS) -> str:
        return (f"Acquisition Started: {status.started}\n"
                f"Max Value: {status.maxval}\n"
                f"Runtime: {status.cnt[cls.ST_RUNTIME]}\n"
                f"Sweeps: {status.cnt[cls.ST_SWEEPS]}\n"
                f"Starts: {status.cnt[cls.ST_STARTS]}")

    @staticmethod
    def acq_setting_text(acq: ACQSETTING) -> str:
        return (f"Range: {acq.range}\n"
                f"CFTFak: {acq.cftfak}\n"
                f"ROI min: {acq.roimin}\n"
                f"ROI max: {acq.roimax}\n"
                f"Regions: {acq.nregions}\n"
                f"Caluse: {acq.caluse}\n"
                f"Calpoints: {acq.calpoints}\n"
                f"Active: {acq.active}\n"
                f"ROI Preset: {acq.eventpreset}")

    @staticmethod
    def dat_setting_text(dat: DATSETTING) -> str:
        fname = dat.filename.decode("utf-8").rstrip("\x00")
        return (f"Savedata: {dat.savedata}\n"
                f"Autoinc: {dat.autoinc}\n"
                f"Format: {dat.fmt}\n"
                f"MPA Format: {dat.mpafmt}\n"
                f"SepHead: {dat.sephead}\n"
                f"Filename: {fname}")

    @staticmethod
    def board_setting_text(board: BOARDSETTING) -> str:
        return (f"Sweepmode: {board.sweepmode}\n"
                f"Prensa: {board.prena}\n"
                f"Cycles: {board.cycles}\n"
                f"Sequences: {board.sequences}\n"
                f"Digio: {board.digio}\n"
                f"Digval: {board.digval}\n"
                f"DAC0: {board.dac0}\n"
                f"DAC1: {board.dac1}\n"
                f"SerNo: {board.serno}\n"
                f"Active: {board.active}\n"
                f"HoldAfter: {board.holdafter}\n"
                f"Swpreset: {board.swpreset}\n"
                f"Fstchan: {board.fstchan}\n"
                f"Timepreset: {board.timepreset}")
