# --- Imports ---
import tkinter as tk
from tkinter import ttk, filedialog
import ctypes
from ctypes import c_int, c_double, c_char, Structure, POINTER, byref
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Optional, Any

REFRESH_RATE = 4000 # ms


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

# --- Structure definitions ---
@dataclass
class ACQSETTING(Structure):
    """Acquisition settings structure"""

    # ctypes structure definition
    _fields_ = [
        ("range", c_int),
        ("cftfak", c_int),
        ("roimin", c_int),
        ("roimax", c_int),
        ("nregions", c_int),
        ("caluse", c_int),
        ("calpoints", c_int),
        ("param", c_int),
        ("offset", c_int),
        ("xdim", c_int),
        ("bitshift", c_int),
        ("active", c_int),
        ("evpreset", c_double),
        ("dummy1", c_double),
        ("dummy2", c_double),
        ("dummy3", c_double)
    ]
    
    # Add settings metadata
    settings_meta = {
        'range': {
            'label': 'Spectrum Length',
            'default': 4096,
            'tooltip': 'Spectrum length (range=)'
        },
        'cftfak': {
            'label': 'CFT Factor',
            'default': 2580100,
            'tooltip': 'LOWORD: 256 * cft factor (t_after_peak / t_to_peak)'
        },
        'roimin': {
            'label': 'ROI Min',
            'default': 0,
            'tooltip': 'Lower ROI limit'
        },
        'roimax': {
            'label': 'ROI Max',
            'default': 4096,
            'tooltip': 'Upper ROI limit'
        },
        'bitshift': {
            'label': 'Bit Shift',
            'default': 0,
            'tooltip': 'LOWORD: Binwidth = 2 ^ (bitshift)'
        },
        'evpreset': {
            'label': 'Event Preset',
            'default': 10.0,
            'tooltip': 'ROI preset value'
        }
    }

@dataclass
class DATSETTING(Structure):
    _fields_ = [
        ("savedata", c_int),
        ("autoinc", c_int),
        ("fmt", c_int),
        ("mpafmt", c_int),
        ("sephead", c_int),
        ("smpts", c_int),
        ("caluse", c_int),
        ("filename", c_char * 256),
        ("specfile", c_char * 256),
        ("command", c_char * 256)
    ]
    
    settings_meta = {
        'savedata': {
            'label': 'Save Data Mode',
            'default': 0,
            'tooltip': '0=No Save at Halt, 1=Save at Halt, 2=Write list file, 3=Write list & Save'
        },
        'autoinc': {
            'label': 'Auto Increment',
            'default': 0,
            'tooltip': 'Enable auto increment of filename'
        },
        'mpafmt': {
            'label': 'MPA Format',
            'default': 0,
            'tooltip': 'Data format: 0=binary, 1=ASCII, 2=CSV'
        },
        'sephead': {
            'label': 'Separate Header',
            'default': 0,
            'tooltip': 'Separate header file (.MP) and data file'
        }
    }

@dataclass
class BOARDSETTING(Structure):
    _fields_ = [
        ("sweepmode", c_int),
        ("prena", c_int),
        ("cycles", c_int),
        ("sequences", c_int),
        ("syncout", c_int),
        ("digio", c_int),
        ("digval", c_int),
        ("dac0", c_int),
        ("dac1", c_int),
        ("dac2", c_int),
        ("dac3", c_int),
        ("dac4", c_int),
        ("dac5", c_int),
        ("fdac", c_int),
        ("tagbits", c_int),
        ("extclk", c_int),
        ("periods", c_int),
        ("serno", c_int),
        ("ddruse", c_int),
        ("active", c_int),
        ("holdafter", c_double),
        ("swpreset", c_double),
        ("fstchan", c_double),
        ("timepreset", c_double)
    ]
    
    settings_meta = {
        'sweepmode': {
            'label': 'Sweep Mode',
            'default': '227ea080',
            'tooltip': 'Hex value controlling measurement mode and features'
        },
        'prena': {
            'label': 'Preset Enable',
            'default': 4,
            'tooltip': 'Bit flags for enabling different presets'
        },
        'cycles': {
            'label': 'Cycles',
            'default': 18,
            'tooltip': 'Number of cycles for sequential mode'
        },
        'sequences': {
            'label': 'Sequences',
            'default': 1,
            'tooltip': 'Number of sequence repetitions'
        },
        'holdafter': {
            'label': 'Hold After',
            'default': 0,
            'tooltip': 'Hold after sweep in units of 64 basic dwelltimes'
        },
        'swpreset': {
            'label': 'Sweep Preset',
            'default': 1000000,
            'tooltip': 'Sweep-Preset value'
        }
    }

class LVCOINCDEF(Structure):
    _fields_ = [
        ("adcnum", c_int),
        ("tofnum", c_int),
        ("ntofs0", c_int),
        ("modules", c_int),
        ("nadcs", c_int)
    ]

class ACQSTATUS(Structure):
    _fields_ = [
        ("started", c_int),
        ("maxval", c_int),
        ("cnt", c_double * 8)
    ]

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

    def run_cmd(self, command: str) -> None:
        """Send a command string to the device."""
        self.dll.RunCmd(0, command.encode('utf-8'))

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

    def get_acq_setting(self) -> ACQSETTING:
        """
        Retrieve the acquisition settings from the device.
        
        Returns:
            ACQSETTING: The acquisition settings structure.
        """
        acq = ACQSETTING()
        self.dll.GetSettingData(byref(acq), self.nDev)
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
        print("  roipreset =", acq.evpreset)

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
                f"ROI Preset: {acq.evpreset}")

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

class MCSDisplay:
    def __init__(self, tab_display: ttk.Frame, mcs: 'MCS8'):
        self.tab_display = tab_display
        self.mcs = mcs
        self.fig = None
        self.axes = []
        self.canvas = None
        self.create_display()

    def create_display(self):
        self._clear_display()
        active_channels, channel_data = self._get_channel_data()
        self._create_plots(active_channels, channel_data)
        self._setup_canvas()
        return self.fig, self.axes, self.canvas

    def update_plot(self):
        try:
            active_channels, channel_data = self._get_channel_data()
            self.create_display()
        except Exception as e:
            print(f"Error updating plot: {e}")

    def _clear_display(self):
        for widget in self.tab_display.winfo_children():
            widget.destroy()

    def _get_channel_data(self) -> Tuple[List[int], Dict[int, List[int]]]:
        acq = self.mcs.get_acq_setting()
        range_val = acq.range
        active_channels = []
        channel_data = {}
        
        for i in range(8):
            data = self.mcs.get_block(0, range_val, channel_id=i)
            if any(x != 0 for x in data):
                active_channels.append(i)
                channel_data[i] = data
        
        return active_channels, channel_data

    def _create_plots(self, active_channels: List[int], channel_data: Dict[int, List[int]]):
        # Create figure with better spacing
        self.fig = Figure(figsize=(8, 2*len(active_channels)), dpi=100)
        
        # Handle both single and multiple channels
        if len(active_channels) == 1:
            self.axes = self.fig.add_subplot(111)  # Single plot
            channel = active_channels[0]
            self._create_subplot(0, channel, channel_data[channel])
            self.axes = [self.axes]  # Wrap in list for consistency
        else:
            self.axes = []
            for idx, channel in enumerate(active_channels):
                ax = self.fig.add_subplot(len(active_channels), 1, idx + 1)
                self._create_subplot(idx, channel, channel_data[channel], ax)
                self.axes.append(ax)
        
        # Add spacing between subplots
        self.fig.subplots_adjust(hspace=0.3)

    def _create_subplot(self, idx: int, channel: int, data: List[int], ax=None):
        if ax is None:
            ax = self.axes  # For single plot case
        
        x = np.arange(len(data))
        ax.plot(x, data, 'b-', linewidth=0.5, label=f'Channel {channel}')
        ax.grid(True, which="both", ls="-", alpha=0.2)
        ax.set_xlabel('Channel')
        ax.set_ylabel('Counts')
        ax.legend(loc='upper right')
        return ax

    def _setup_canvas(self):
        self.fig.tight_layout(pad=3.0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_display)
        self.canvas.draw()
        
        toolbar = NavigationToolbar2Tk(self.canvas, self.tab_display)
        toolbar.update()
        
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

class MCSUI:
    def __init__(self, mcs: 'MCS8'):
        self.rev_count = 0
        self.dl_warning_shown = False
        self.mcs = mcs
        self.root = tk.Tk()
        self.display = None
        self.status_labels = {}
        self._setup_ui()
        self.filename = None
        self.check_DLL()
        

    def check_DLL(self):
        if (self.mcs.check_status() == 0 and self.dl_warning_shown == False):
            self.dl_warning_shown = True
            tk.messagebox.showwarning("No DLL active!", "MCS8 not connected. Please start the DLL first.")
            
    
    def _setup_ui(self):
        self._setup_window()
        self._create_controls()
        self._create_notebook()
        self._setup_display()
        self._start_refresh_timer()

    def _setup_window(self):
        self.root.title("MCS8 Measurement Control")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        
    def update_filename(self, event):
        text = event.widget.get()
        self.filename = text

    def _create_controls(self):
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=0, column=0, sticky="ew")

        # Create and configure buttons with tooltips
        start_btn = ttk.Button(button_frame, text="▶", command=self.mcs.start)
        stop_btn = ttk.Button(button_frame, text="■", command=self.mcs.halt)
        continue_btn = ttk.Button(button_frame, text="⏵", command=self.mcs.continue_device)
        erase_btn = ttk.Button(button_frame, text="⌫", command=self.mcs.erase)

        # Add tooltips
        CreateToolTip(start_btn, "Start Measurement")
        CreateToolTip(stop_btn, "Stop Measurement")
        CreateToolTip(continue_btn, "Continue Measurement")
        CreateToolTip(erase_btn, "Erase Data")

        # Grid layout
        start_btn.grid(row=0, column=0, padx=5)
        stop_btn.grid(row=0, column=1, padx=5)
        continue_btn.grid(row=0, column=2, padx=5)
        erase_btn.grid(row=0, column=3, padx=5)

        filename_frame = ttk.Frame(button_frame)
        filename_frame.grid(row=1, column=0, columnspan=5, pady=5)

        ttk.Label(filename_frame, text="MPA Filename:").pack(side=tk.LEFT, padx=5)
        self.filename_entry = ttk.Entry(filename_frame, width=40)
        self.filename_entry.pack(side=tk.LEFT, padx=5)
        
        # update filename if entry is changed
        self.filename_entry.bind("<FocusOut>", self.update_filename)
        

        ttk.Button(filename_frame, text="Browse", command=self._browse_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(filename_frame, text="Load MPA", command=self._load_mpa).pack(side=tk.LEFT, padx=5)
        ttk.Button(filename_frame, text="Save Config", command=self.mcs.save_cnf).pack(side=tk.LEFT, padx=5)
        ttk.Button(filename_frame, text="Save MPA", command=self.mcs.savempa).pack(side=tk.LEFT, padx=5)

    def _browse_file(self):
        filename = filedialog.askopenfilename(
            defaultextension=".mpa",
            filetypes=[("MPA files", "*.mpa"), ("All files", "*.*")]
        )
        if filename:
            self.filename_entry.delete(0, tk.END)
            self.filename_entry.insert(0, filename)
            self.mcs.set_mpaname(filename)
            self.filename = filename
            self.mcs.run_cmd(f"loadmpa {self.filename}")
            self.display.update_plot()

    def _load_mpa(self):

        if self.filename:
            self.mcs.set_mpaname(self.filename)
            try:
                self.mcs.run_cmd(f"loadmpa {self.filename}")
                self.display.update_plot()
            except Exception as e:
                print(f"Error loading MPA file: {e}")

    def _create_settings_tab(self, tab, settings_class, title):
        """Create a settings tab with status display and scrollable settings"""
        # Create main frame to hold both status and settings
        main_frame = ttk.Frame(tab)
        main_frame.pack(expand=True, fill="both")
        
        # Create status frame at the top
        status_frame = ttk.LabelFrame(main_frame, text="Current Status")
        status_frame.pack(fill='x', padx=5, pady=5)
        
        # Add status label
        self.status_labels[title] = ttk.Label(
            status_frame, 
            text="", 
            relief="sunken", 
            padding="5",
            anchor="nw",
            justify="left"
        )
        self.status_labels[title].pack(expand=True, fill="both", padx=5, pady=5)

        # Create settings frame
        settings_frame = ttk.Frame(main_frame)
        settings_frame.pack(expand=True, fill="both", padx=5, pady=5)

        # Create scrollable frame
        canvas = tk.Canvas(settings_frame)
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Create settings dictionary and widgets
        settings_dict = {}
        for field_name, meta in settings_class.settings_meta.items():
            settings_dict[field_name] = {
                'label': meta['label'],
                'value': tk.StringVar(value=str(meta['default'])),
                'tooltip': meta['tooltip']
            }

        # Create header
        header = ttk.Label(scrollable_frame, text=f"{title} Configuration", 
                          font=('TkDefaultFont', 10, 'bold'))
        header.pack(fill='x', padx=5, pady=5)

        # Create settings widgets
        for setting, data in settings_dict.items():
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill='x', padx=5, pady=2)

            label = ttk.Label(frame, text=f"{data['label']}:", width=20, anchor='e')
            label.pack(side='left', padx=5)

            entry = ttk.Entry(frame, textvariable=data['value'])
            entry.pack(side='left', fill='x', expand=True, padx=5)
            
            CreateToolTip(entry, data['tooltip'])

            apply_btn = ttk.Button(frame, text="Apply", 
                                 command=lambda s=setting, t=title.lower(): 
                                        self._apply_setting(s, t))
            apply_btn.pack(side='right', padx=5)

        return settings_dict

    def _create_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Create tabs
        self.tab_status = ttk.Frame(self.notebook)
        self.tab_acq = ttk.Frame(self.notebook)
        self.tab_dat = ttk.Frame(self.notebook)
        self.tab_board = ttk.Frame(self.notebook)
        self.tab_display = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.tab_status, text="AcqStatus")
        self.notebook.add(self.tab_acq, text="AcqSettings")
        self.notebook.add(self.tab_dat, text="DatSettings")
        self.notebook.add(self.tab_board, text="BoardSettings")
        self.notebook.add(self.tab_display, text="DataDisplay")

        # Create settings for each tab
        self.acq_settings = self._create_settings_tab(
            self.tab_acq, ACQSETTING, "Acquisition Settings")
        self.dat_settings = self._create_settings_tab(
            self.tab_dat, DATSETTING, "Data Settings")
        self.board_settings = self._create_settings_tab(
            self.tab_board, BOARDSETTING, "Board Settings")
        
        # Bind tab changed event
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        self.status_label = ttk.Label(self.tab_status, text="", relief="sunken", padding="5", anchor="nw", justify="left")
        self.status_label.pack(expand=True, fill="both", padx=5, pady=5)

    def _apply_setting(self, setting: str, settings_type: str):
        """Apply the changed setting to the device"""
        try:
            # Get the appropriate settings dictionary
            
            if 'acq' in settings_type:
                settings_dict = self.acq_settings
            elif 'dat' in settings_type:
                settings_dict = self.dat_settings
            else:
                settings_dict = self.board_settings
            
            value = settings_dict[setting]['value'].get()
            
            # Handle special cases
            if setting == 'sweepmode' and not value.startswith('0x'):
                value = f"0x{value}"
            
            command = f"{setting}={value}"
            self.mcs.run_cmd(command)
            self._update_settings_display()
        except Exception as e:
            print(f"Error applying setting: {e}")

    def _update_settings_display(self):
        """Update all settings displays with current values"""
        try:
            acq = self.mcs.get_acq_setting()
            dat = self.mcs.get_dat_setting()
            board = self.mcs.get_mcs_setting()
            
            # Update acquisition settings
            for key in self.acq_settings:
                self.acq_settings[key]['value'].set(str(getattr(acq, key)))
            
            # Update data settings
            for key in self.dat_settings:
                self.dat_settings[key]['value'].set(str(getattr(dat, key)))
            
            # Update board settings
            for key in self.board_settings:
                value = getattr(board, key)
                if key == 'sweepmode':
                    value = f"{value:08x}"
                self.board_settings[key]['value'].set(str(value))
                
        except Exception as e:
            print(f"Error updating settings display: {e}")

    def _start_refresh_timer(self):
        self._refresh_view()
        self.root.after(REFRESH_RATE, self._start_refresh_timer)
        
    def _refresh_view(self):
        """Update all status displays and labels"""
        self.rev_count += 1
        if self.rev_count > 3:
            self.rev_count = 0
            self.check_DLL()
            
        
        try:
            current_tab = self.notebook.select()
            # Get the tab index of the display tab (last tab)
            display_tab = self.notebook.tabs()[-1]
            
            if current_tab != display_tab:
            
                status = self.mcs.get_status()
                acq = self.mcs.get_acq_setting()
                dat = self.mcs.get_dat_setting()
                board = self.mcs.get_mcs_setting()

                # Update main status tab
                self.status_label.config(text=MCS8.status_text(status))

                # Update status labels in each settings tab
                self.status_labels["Acquisition Settings"].config(
                    text=MCS8.acq_setting_text(acq)
                )
                self.status_labels["Data Settings"].config(
                    text=MCS8.dat_setting_text(dat)
                )
                self.status_labels["Board Settings"].config(
                    text=MCS8.board_setting_text(board)
                )

            # Schedule next refresh
            refresh_ms = int(self.refresh_rate.get() if hasattr(self, 'refresh_rate') else REFRESH_RATE)
            self.root.after(refresh_ms, self._refresh_view)
        except Exception as e:
            print(f"Error in refresh: {e}")
            self.root.after(REFRESH_RATE, self._refresh_view)

    def _on_tab_changed(self, event):
        # Get the newly selected tab
        current_tab = self.notebook.select()
        # Get the tab index of the display tab (last tab)
        display_tab = self.notebook.tabs()[-1]
        
        # Only update if we are switching TO the display tab
        if current_tab == display_tab and self.notebook.select() != self._last_tab:
            self.display.update_plot()
        
        # Store the current tab for next comparison
        self._last_tab = current_tab

    def _setup_display(self):
        """Setup the display tab with plot and refresh controls"""
        # Initialize display instance
        self.display = MCSDisplay(self.tab_display, self.mcs)
        
        # Create control frame
        control_frame = ttk.Frame(self.tab_display)
        control_frame.pack(fill='x', side='top', padx=5, pady=5)
        
        # Add manual refresh button
        refresh_btn = ttk.Button(
            control_frame,
            text="Refresh Now",
            command=self.display.update_plot
        )
        refresh_btn.pack(side='left', padx=5)

def main_cmd():
    mcs = MCS8()  # Initialize the wrapper
    # Run the integrated command loop
    mcs.run_command_loop()

def main_ui():
    mcs = MCS8()
    ui = MCSUI(mcs)
    ui.root.mainloop()

if __name__ == '__main__':
    main_ui()
