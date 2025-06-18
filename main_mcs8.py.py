# --- Imports ---
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from mcs8_func import MCS8, CreateToolTip
from plot_display import MCSDisplay
from structures import *

REFRESH_RATE = 4000  # ms


class BitfieldEditor:
    """Dialog for editing bitfield values"""
    
    def __init__(self, parent, field_name, var, label):
        self.parent = parent
        self.field_name = field_name
        self.var = var
        self.label = label
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit {label} Bits")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_ui()
        self._load_current_value()

    def _create_ui(self):
        """Create the bitfield editor UI"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        ttk.Label(main_frame, text=f"Edit {self.label}", 
                 font=('TkDefaultFont', 10, 'bold')).pack(pady=(0, 10))
        
        # Current value display
        value_frame = ttk.Frame(main_frame)
        value_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(value_frame, text="Current Value:").pack(side='left')
        self.value_label = ttk.Label(value_frame, text="0", font=('Courier', 10))
        self.value_label.pack(side='left', padx=10)
        
        # Bit checkboxes frame
        bits_frame = ttk.LabelFrame(main_frame, text="Individual Bits")
        bits_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Create scrollable frame for bits
        canvas = tk.Canvas(bits_frame)
        scrollbar = ttk.Scrollbar(bits_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create bit checkboxes (16 bits)
        self.bit_vars = {}
        for i in range(16):
            var = tk.BooleanVar()
            var.trace('w', self._update_value)
            cb = ttk.Checkbutton(scrollable_frame, text=f"Bit {i}", variable=var)
            cb.pack(anchor='w', padx=5, pady=1)
            self.bit_vars[i] = var
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x')
        
        ttk.Button(button_frame, text="OK", command=self._ok_clicked).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._cancel_clicked).pack(side='right')

    def _load_current_value(self):
        """Load current value into bit checkboxes"""
        try:
            current_value = int(self.var.get())
            for bit, var in self.bit_vars.items():
                var.set(bool(current_value & (1 << bit)))
            self._update_value()
        except ValueError:
            self.value_label.config(text="Invalid value")

    def _update_value(self, *args):
        """Update value display based on bit checkboxes"""
        value = 0
        for bit, var in self.bit_vars.items():
            if var.get():
                value |= (1 << bit)
        
        self.value_label.config(text=f"0x{value:04x} ({value})")

    def _ok_clicked(self):
        """Apply changes and close dialog"""
        value = 0
        for bit, var in self.bit_vars.items():
            if var.get():
                value |= (1 << bit)
        
        self.var.set(str(value))
        self.dialog.destroy()

    def _cancel_clicked(self):
        """Close dialog without applying changes"""
        self.dialog.destroy()


class MCSUI:
    """
    Enhanced MCS8 User Interface with integrated Channel Settings
    """

    def __init__(self, mcs: 'MCS8'):
        self.rev_count = 0
        self.dl_warning_shown = False
        self.mcs = mcs
        self.root = tk.Tk()
        self.display = None
        self.status_labels = {}
        
        # Command line interface variables
        self.command_history = []
        self.history_index = -1
        
        # Performance optimization flags
        self.display_update_pending = False
        self.display_update_interval = 500  # ms 
        self.status_update_interval = 1000  # ms 
        
        # Channel settings variables
        self.current_channel = 0
        self.max_channels = 8
        self.auto_refresh_channels = tk.BooleanVar(value=True)
        self.refresh_interval = 2000  # ms
        self.refresh_job = None
        self.modified_settings = set()
        self.channel_widgets = {}
        
        # Command mapping for MCS8 parameters
        self.command_mapping = {
            # Acquisition Settings
            'range': 'range',
            'roimin': 'roimin', 
            'roimax': 'roimax',
            'eventpreset': 'eventpreset',
            'bitshift': 'bitshift',
            'active': 'active',
            
            # Board Settings  
            'sweepmode': 'sweepmode',
            'prena': 'prena',
            'cycles': 'cycles',
            'sequences': 'sequences',
            'swpreset': 'swpreset',
            'timepreset': 'rtpreset',  # Note: rtpreset in command
            'holdafter': 'holdafter',
            'fstchan': 'fstchan',
            'tagbits': 'tagbits',
            'periods': 'periods',
            'digio': 'digio',
            'syncout': 'syncout',
            
            # DAC Settings
            'dac0': 'vdac0',
            'dac1': 'vdac1', 
            'dac2': 'vdac2',
            'dac3': 'vdac3',
            'dac4': 'vdac4',
            'dac5': 'vdac5',
            
            # Data Settings
            'savedata': 'savedata',
            'autoinc': 'autoinc',
            'fmt': 'fmt',
            'mpafmt': 'mpafmt',
            'sephead': 'sephead'
        }
        
        # Voltage DAC mapping
        self.voltage_dac_mapping = {
            'dac0': 'dac0v',
            'dac1': 'dac1v',
            'dac2': 'dac2v', 
            'dac3': 'dac3v',
            'dac4': 'dac4v',
            'dac5': 'dac5v'
        }
        
        self._setup_ui()
        self.filename = None
        self.check_DLL()
        
        # Set initial window size
        self.root.geometry("1200x900")
        self.root.update_idletasks()
        
    def check_DLL(self):
        if (self.mcs.check_status() == 0 and self.dl_warning_shown == False):
            self.dl_warning_shown = True
            messagebox.showwarning("No DLL active!", "MCS8 not connected. Please start the DLL first.")
            
    def _setup_ui(self):
        self._setup_window()
        self._create_menu_bar()
        self._create_controls()
        self._create_notebook()
        self._setup_display()
        self._create_command_line_interface()
        self._start_refresh_timer()

    def _setup_window(self):
        self.root.title("MCS8 Measurement Control - Advanced")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)
        
        # Keyboard shortcuts
        self.root.bind('<Control-grave>', lambda e: self._toggle_command_interface())
        self.root.bind('<Control-s>', lambda e: self._focus_channel_settings())
        self.root.bind('<F5>', lambda e: self._manual_refresh_all())
        self.root.bind('<Control-r>', lambda e: self._load_all_settings())
        
        self._set_window_icon()
        
    def _create_menu_bar(self):
        """Create menu bar with settings and help options"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Settings Menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        
        settings_menu.add_command(
            label="Focus Channel Settings",
            command=self._focus_channel_settings,
            accelerator="Ctrl+S"
        )
        settings_menu.add_separator()
        settings_menu.add_command(
            label="Refresh All",
            command=self._manual_refresh_all,
            accelerator="F5"
        )
        settings_menu.add_command(
            label="Save Configuration",
            command=self.mcs.save_cnf
        )
        settings_menu.add_command(
            label="Load Configuration",
            command=self._load_all_settings,
            accelerator="Ctrl+R"
        )
        
        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _set_window_icon(self):
        """Set the window icon with fallback options"""
        icon_paths = ['fast.ico']
        
        for icon_path in icon_paths:
            try:
                self.root.iconbitmap(icon_path)
                return
            except (tk.TclError, FileNotFoundError):
                continue
        
        # Try image formats if no .ico file works
        image_paths = ['logo.png', 'mcs8_logo.png', 'assets/logo.png']
        for img_path in image_paths:
            try:
                icon_image = tk.PhotoImage(file=img_path)
                self.root.iconphoto(True, icon_image)
                self.root.icon_image = icon_image
                return
            except (tk.TclError, FileNotFoundError):
                continue

    def update_filename(self, event):
        text = event.widget.get()
        self.filename = text

    def _create_controls(self):
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=0, column=0, sticky="ew")

        # Control buttons - Row 0
        start_btn = ttk.Button(button_frame, text="▶", command=self._start)
        stop_btn = ttk.Button(button_frame, text="■", command=self._stop)
        continue_btn = ttk.Button(button_frame, text="⏵", command=self._continue)
        erase_btn = ttk.Button(button_frame, text="⌫", command=self._erase)

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

        # Filename controls - Row 1
        filename_frame = ttk.Frame(button_frame)
        filename_frame.grid(row=1, column=0, columnspan=5, pady=5)

        ttk.Label(filename_frame, text="MPA Filename:").pack(side=tk.LEFT, padx=5)
        self.filename_entry = ttk.Entry(filename_frame, width=40)
        self.filename_entry.pack(side=tk.LEFT, padx=5)
        
        self.filename_entry.bind("<FocusOut>", self.update_filename)
        
        ttk.Button(filename_frame, text="Set Filename", command=self._set_filename_from_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(filename_frame, text="Browse", command=self._browse_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(filename_frame, text="Load MPA", command=self._load_mpa).pack(side=tk.LEFT, padx=5)
        ttk.Button(filename_frame, text="Save Config", command=self.mcs.save_cnf).pack(side=tk.LEFT, padx=5)
        ttk.Button(filename_frame, text="Save MPA", command=self.mcs.savempa).pack(side=tk.LEFT, padx=5)

    def _start(self):
        """Start data acquisition with display refresh"""
        if self.display:
            self.display._clear_display()
        self.mcs.start()
        if self.display:
            self.root.after(1000, lambda: self.display.create_display())

    def _stop(self):
        """Stop data acquisition with display refresh"""
        if self.display:
            self.display._clear_display()
        self.mcs.halt()
        if self.display:
            self.root.after(1000, lambda: self.display.create_display())

    def _continue(self):
        """Continue data acquisition with display refresh"""
        if self.display:
            self.display._clear_display()
        self.mcs.continue_device()
        if self.display:
            self.root.after(1000, lambda: self.display.create_display())

    def _erase(self):
        """Erase data with display refresh"""
        if self.display:
            self.display._clear_display()
        self.mcs.erase()
        if self.display:
            self.root.after(1000, lambda: self.display.create_display())

    def _set_filename_from_entry(self):
        """Set the filename in the MCS device from the entry field"""
        filename = self.filename_entry.get()
        if filename:
            self.filename = filename
            self.mcs.set_mpaname(filename)

    def _create_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Create tabs
        self.tab_status = ttk.Frame(self.notebook)
        self.tab_acq = ttk.Frame(self.notebook)
        self.tab_dat = ttk.Frame(self.notebook)
        self.tab_board = ttk.Frame(self.notebook)
        self.tab_channels = ttk.Frame(self.notebook)  # New integrated channel tab
        self.tab_display = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.tab_status, text="AcqStatus")
        self.notebook.add(self.tab_acq, text="AcqSettings")
        self.notebook.add(self.tab_dat, text="DatSettings")
        self.notebook.add(self.tab_board, text="BoardSettings")
        self.notebook.add(self.tab_channels, text="Channel Settings")
        self.notebook.add(self.tab_display, text="DataDisplay")

        # Create settings for existing tabs
        self.acq_settings = self._create_settings_tab(
            self.tab_acq, ACQSETTING, "Acquisition Settings")
        self.dat_settings = self._create_settings_tab(
            self.tab_dat, DATSETTING, "Data Settings")
        self.board_settings = self._create_settings_tab(
            self.tab_board, BOARDSETTING, "Board Settings")
        
        # Create the new integrated channel settings tab
        self._create_channel_settings_tab()
        
        # Bind tab changed event
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        # Status tab
        self.status_label = ttk.Label(self.tab_status, text="", relief="sunken", padding="5", anchor="nw", justify="left")
        self.status_label.pack(expand=True, fill="both", padx=5, pady=5)

    def _create_channel_settings_tab(self):
        """Create the integrated channel settings tab"""
        # Main container
        main_container = ttk.Frame(self.tab_channels)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Top control frame
        control_frame = ttk.LabelFrame(main_container, text="Channel Control")
        control_frame.pack(fill='x', pady=(0, 5))
        
        # Channel selection and auto-refresh
        top_controls = ttk.Frame(control_frame)
        top_controls.pack(fill='x', padx=10, pady=5)
        
        # Channel selector
        ttk.Label(top_controls, text="Channel:").pack(side='left')
        self.channel_var = tk.IntVar(value=self.current_channel)
        channel_combo = ttk.Combobox(
            top_controls,
            textvariable=self.channel_var,
            values=list(range(self.max_channels)),
            state='readonly',
            width=5
        )
        channel_combo.pack(side='left', padx=5)
        channel_combo.bind('<<ComboboxSelected>>', self._on_channel_change)
        
        # Auto refresh checkbox
        auto_refresh_cb = ttk.Checkbutton(
            top_controls,
            text="Auto Refresh",
            variable=self.auto_refresh_channels,
            command=self._toggle_channel_auto_refresh
        )
        auto_refresh_cb.pack(side='left', padx=20)
        
        # Manual refresh button
        ttk.Button(
            top_controls,
            text="Refresh Now",
            command=self._manual_refresh_channels
        ).pack(side='left', padx=5)
        
        # Status indicator
        self.channel_status_label = ttk.Label(
            top_controls,
            text="Ready",
            foreground="green"
        )
        self.channel_status_label.pack(side='right', padx=10)
        
        # Create notebook for channel setting categories
        self.channel_notebook = ttk.Notebook(main_container)
        self.channel_notebook.pack(fill='both', expand=True)
        
        # Create tabs for different setting categories
        self._create_channel_acquisition_tab()
        self._create_channel_timing_tab()
        self._create_channel_dac_tab()
        self._create_channel_advanced_tab()
        self._create_channel_data_tab()
        
        # Bottom button frame
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill='x', pady=(5, 0))
        
        # Left side buttons
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side='left')
        
        ttk.Button(left_frame, text="Load All Settings", 
                  command=self._load_channel_settings).pack(side='left', padx=5)
        ttk.Button(left_frame, text="Save Config", 
                  command=self.mcs.save_cnf).pack(side='left', padx=5)
        
        # Right side buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side='right')
        
        ttk.Button(right_frame, text="Apply All Changes", 
                  command=self._apply_all_channel_changes).pack(side='left', padx=5)
        ttk.Button(right_frame, text="Reset Changes", 
                  command=self._reset_channel_changes).pack(side='left', padx=5)

    def _create_channel_acquisition_tab(self):
        """Create the channel acquisition settings tab"""
        tab = ttk.Frame(self.channel_notebook)
        self.channel_notebook.add(tab, text="Acquisition")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Acquisition settings
        acq_frame = ttk.LabelFrame(scrollable_frame, text="Spectrum Configuration")
        acq_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(acq_frame, 'range', ACQSETTING, 'Spectrum Length')
        self._create_channel_setting_widget(acq_frame, 'roimin', ACQSETTING, 'ROI Minimum')
        self._create_channel_setting_widget(acq_frame, 'roimax', ACQSETTING, 'ROI Maximum')
        self._create_channel_setting_widget(acq_frame, 'eventpreset', ACQSETTING, 'Event Preset')
        self._create_channel_setting_widget(acq_frame, 'bitshift', ACQSETTING, 'Bit Shift')
        self._create_channel_setting_widget(acq_frame, 'active', ACQSETTING, 'Active Mode')

    def _create_channel_timing_tab(self):
        """Create the channel timing settings tab"""
        tab = ttk.Frame(self.channel_notebook)
        self.channel_notebook.add(tab, text="Timing")
        
        # Preset settings
        preset_frame = ttk.LabelFrame(tab, text="Preset Configuration")
        preset_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(preset_frame, 'prena', BOARDSETTING, 'Preset Enable', widget_type='bitfield')
        
        # Timing values
        timing_frame = ttk.LabelFrame(tab, text="Timing Values")
        timing_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(timing_frame, 'swpreset', BOARDSETTING, 'Sweep Preset')
        self._create_channel_setting_widget(timing_frame, 'timepreset', BOARDSETTING, 'Time Preset (s)')
        self._create_channel_setting_widget(timing_frame, 'holdafter', BOARDSETTING, 'Hold After')
        self._create_channel_setting_widget(timing_frame, 'fstchan', BOARDSETTING, 'First Channel Delay')
        
        # Sequential mode
        seq_frame = ttk.LabelFrame(tab, text="Sequential Mode")
        seq_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(seq_frame, 'cycles', BOARDSETTING, 'Cycles')
        self._create_channel_setting_widget(seq_frame, 'sequences', BOARDSETTING, 'Sequences')
        self._create_channel_setting_widget(seq_frame, 'periods', BOARDSETTING, 'Periods')

    def _create_channel_dac_tab(self):
        """Create the channel DAC settings tab"""
        tab = ttk.Frame(self.channel_notebook)
        self.channel_notebook.add(tab, text="DAC/Voltages")
        
        # Voltage settings
        voltage_frame = ttk.LabelFrame(tab, text="DAC Voltage Settings")
        voltage_frame.pack(fill='x', padx=5, pady=5)
        
        # Create voltage controls for each DAC
        for i in range(6):
            dac_name = f'dac{i}'
            label = f'DAC{i} Voltage' + (' (START)' if i == 0 else f' (STOP{i})')
            self._create_voltage_widget(voltage_frame, dac_name, label)
        
        # Hex DAC values
        hex_frame = ttk.LabelFrame(tab, text="DAC Hex Values")
        hex_frame.pack(fill='x', padx=5, pady=5)
        
        for i in range(6):
            dac_name = f'dac{i}'
            label = f'DAC{i} Hex Value'
            self._create_channel_setting_widget(hex_frame, dac_name, BOARDSETTING, label, widget_type='hex')

    def _create_channel_advanced_tab(self):
        """Create the channel advanced settings tab"""
        tab = ttk.Frame(self.channel_notebook)
        self.channel_notebook.add(tab, text="Advanced")
        
        # Sweep mode with detailed configuration
        mode_frame = ttk.LabelFrame(tab, text="Sweep Mode Configuration")
        mode_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(mode_frame, 'sweepmode', BOARDSETTING, 'Sweep Mode', widget_type='hex')
        
        # Digital I/O
        dio_frame = ttk.LabelFrame(tab, text="Digital I/O Configuration")
        dio_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(dio_frame, 'digio', BOARDSETTING, 'Digital I/O', widget_type='bitfield')
        self._create_channel_setting_widget(dio_frame, 'syncout', BOARDSETTING, 'Sync Output')
        
        # Advanced settings
        advanced_frame = ttk.LabelFrame(tab, text="Advanced Configuration")
        advanced_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(advanced_frame, 'tagbits', BOARDSETTING, 'Tag Bits')

    def _create_channel_data_tab(self):
        """Create the channel data settings tab"""
        tab = ttk.Frame(self.channel_notebook)
        self.channel_notebook.add(tab, text="Data")
        
        # Data format settings
        format_frame = ttk.LabelFrame(tab, text="Data Format")
        format_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(format_frame, 'savedata', DATSETTING, 'Save Data Mode')
        self._create_channel_setting_widget(format_frame, 'autoinc', DATSETTING, 'Auto Increment')
        self._create_channel_setting_widget(format_frame, 'fmt', DATSETTING, 'Format Type')
        self._create_channel_setting_widget(format_frame, 'mpafmt', DATSETTING, 'MPA Format')
        self._create_channel_setting_widget(format_frame, 'sephead', DATSETTING, 'Separate Header')

    def _create_channel_setting_widget(self, parent, field_name, structure_class, label, widget_type='entry'):
        """Create a channel setting widget with label, entry, and apply button"""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=2)
        
        # Label
        label_widget = ttk.Label(frame, text=f"{label}:", width=20, anchor='e')
        label_widget.pack(side='left', padx=5)
        
        # Get metadata if available
        meta = getattr(structure_class, 'settings_meta', {}).get(field_name, {})
        tooltip = meta.get('tooltip', f'Set {label}')
        
        # Value variable
        var = tk.StringVar()
        
        # Create appropriate widget based on type
        if widget_type == 'hex':
            entry = ttk.Entry(frame, textvariable=var, width=15)
            entry.pack(side='left', padx=5)
        elif widget_type == 'bitfield':
            entry = ttk.Entry(frame, textvariable=var, width=15)
            entry.pack(side='left', padx=5)
            # Add bitfield helper button
            bit_btn = ttk.Button(frame, text="Edit Bits", 
                               command=lambda: self._open_bitfield_editor(field_name, var, label))
            bit_btn.pack(side='left', padx=2)
        else:
            entry = ttk.Entry(frame, textvariable=var, width=15)
            entry.pack(side='left', padx=5)
        
        # Bind change event to track modifications
        var.trace('w', lambda *args, fn=field_name: self._mark_channel_modified(fn))
        
        # Status indicator
        status_label = ttk.Label(frame, text="●", foreground="green", width=2)
        status_label.pack(side='left')
        
        # Apply button
        apply_btn = ttk.Button(frame, text="Apply", 
                             command=lambda: self._apply_channel_setting(field_name, var.get(), status_label))
        apply_btn.pack(side='right', padx=5)
        
        # Store widget references
        self.channel_widgets[field_name] = {
            'var': var,
            'entry': entry,
            'status': status_label,
            'structure': structure_class,
            'meta': meta
        }
        
        # Add tooltip
        CreateToolTip(entry, tooltip)

    def _create_voltage_widget(self, parent, dac_name, label):
        """Create a voltage setting widget with -/+ buttons"""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=2)
        
        # Label
        ttk.Label(frame, text=f"{label}:", width=20, anchor='e').pack(side='left', padx=5)
        
        # Decrease button
        decrease_btn = ttk.Button(frame, text="-", width=3,
                                command=lambda: self._adjust_voltage(dac_name, -0.001))
        decrease_btn.pack(side='left', padx=2)
        
        # Voltage entry
        var = tk.StringVar(value="0.000")
        entry = ttk.Entry(frame, textvariable=var, width=10, justify='center')
        entry.pack(side='left', padx=2)
        
        # Increase button  
        increase_btn = ttk.Button(frame, text="+", width=3,
                                command=lambda: self._adjust_voltage(dac_name, 0.001))
        increase_btn.pack(side='left', padx=2)
        
        # Apply button
        apply_btn = ttk.Button(frame, text="Set Voltage",
                             command=lambda: self._apply_voltage(dac_name, var.get()))
        apply_btn.pack(side='right', padx=5)
        
        # Store reference
        self.channel_widgets[f'{dac_name}_voltage'] = {
            'var': var,
            'entry': entry
        }
        
        CreateToolTip(entry, f"Set {label} in Volts")

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

    # Channel Settings Methods
    def _load_channel_settings(self):
        """Load current channel settings from the device"""
        try:
            self._update_channel_status("Loading settings...", "orange")
            
            # Get current settings from device
            acq = self.mcs.get_acq_setting(self.current_channel)
            dat = self.mcs.get_dat_setting()
            board = self.mcs.get_mcs_setting()
            
            # Update widgets with current values
            for field_name, widget_info in self.channel_widgets.items():
                if field_name.endswith('_voltage'):
                    continue  # Skip voltage widgets for now
                    
                structure = widget_info['structure']
                
                if structure == ACQSETTING:
                    value = getattr(acq, field_name, '')
                elif structure == DATSETTING:
                    value = getattr(dat, field_name, '')
                elif structure == BOARDSETTING:
                    value = getattr(board, field_name, '')
                else:
                    continue
                
                # Format value appropriately
                if field_name == 'sweepmode':
                    widget_info['var'].set(f"{value:08x}")
                else:
                    widget_info['var'].set(str(value))
                
                # Reset status indicator
                widget_info['status'].config(foreground="green")
            
            # Clear modified settings
            self.modified_settings.clear()
            
            self._update_channel_status("Settings loaded", "green")
            
        except Exception as e:
            self._update_channel_status(f"Error loading settings: {e}", "red")
            messagebox.showerror("Error", f"Failed to load settings: {e}")

    def _apply_channel_setting(self, field_name, value, status_label):
        """Apply a single channel setting to the device"""
        try:
            # Get command name
            command_name = self.command_mapping.get(field_name)
            if not command_name:
                raise ValueError(f"No command mapping for {field_name}")
            
            # Format value for command
            if field_name == 'sweepmode':
                if not value.startswith('0x'):
                    value = f"0x{value}"
            
            # Send command
            command = f"{command_name}={value}"
            self.mcs.run_cmd(command)
            
            # Update status
            status_label.config(foreground="green")
            self.modified_settings.discard(field_name)
            
            self._update_channel_status(f"Applied: {command}", "green")
            self._append_to_output(f"Channel Command: {command}\n")
            
        except Exception as e:
            status_label.config(foreground="red")
            self._update_channel_status(f"Error: {e}", "red")
            messagebox.showerror("Error", f"Failed to apply {field_name}: {e}")

    def _apply_voltage(self, dac_name, voltage_str):
        """Apply voltage setting to DAC"""
        try:
            voltage = float(voltage_str)
            command_name = self.voltage_dac_mapping.get(dac_name)
            if not command_name:
                raise ValueError(f"No voltage command mapping for {dac_name}")
            
            command = f"{command_name}={voltage:.3f}"
            self.mcs.run_cmd(command)
            
            self._update_channel_status(f"Applied: {command}", "green")
            self._append_to_output(f"Voltage Command: {command}\n")
            
        except Exception as e:
            self._update_channel_status(f"Error: {e}", "red")
            messagebox.showerror("Error", f"Failed to set voltage: {e}")

    def _adjust_voltage(self, dac_name, delta):
        """Adjust voltage by delta amount"""
        widget_info = self.channel_widgets.get(f'{dac_name}_voltage')
        if widget_info:
            try:
                current = float(widget_info['var'].get())
                new_voltage = current + delta
                widget_info['var'].set(f"{new_voltage:.3f}")
            except ValueError:
                widget_info['var'].set("0.000")

    def _apply_all_channel_changes(self):
        """Apply all modified channel settings"""
        if not self.modified_settings:
            messagebox.showinfo("Info", "No changes to apply")
            return
        
        try:
            applied_count = 0
            for field_name in list(self.modified_settings):
                widget_info = self.channel_widgets.get(field_name)
                if widget_info:
                    value = widget_info['var'].get()
                    self._apply_channel_setting(field_name, value, widget_info['status'])
                    applied_count += 1
            
            messagebox.showinfo("Success", f"Applied {applied_count} changes")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error applying changes: {e}")

    def _reset_channel_changes(self):
        """Reset all channel changes and reload from device"""
        if self.modified_settings:
            result = messagebox.askyesno("Confirm Reset", 
                                       "This will discard all unsaved changes. Continue?")
            if result:
                self._load_channel_settings()

    def _mark_channel_modified(self, field_name):
        """Mark a channel setting as modified"""
        self.modified_settings.add(field_name)
        widget_info = self.channel_widgets.get(field_name)
        if widget_info and 'status' in widget_info:
            widget_info['status'].config(foreground="orange")

    def _update_channel_status(self, message, color="black"):
        """Update channel status label"""
        if hasattr(self, 'channel_status_label'):
            self.channel_status_label.config(text=message, foreground=color)

    def _on_channel_change(self, event=None):
        """Handle channel selection change"""
        self.current_channel = self.channel_var.get()
        self._load_channel_settings()

    def _manual_refresh_channels(self):
        """Manually refresh channel settings"""
        self._load_channel_settings()

    def _toggle_channel_auto_refresh(self):
        """Toggle auto refresh for channels on/off"""
        if self.auto_refresh_channels.get():
            self._start_channel_auto_refresh()
        else:
            self._stop_channel_auto_refresh()

    def _start_channel_auto_refresh(self):
        """Start auto refresh timer for channels"""
        if self.auto_refresh_channels.get() and self.root.winfo_exists():
            # Only refresh if on channel tab
            current_tab = self.notebook.select()
            if current_tab == str(self.tab_channels):
                self._load_channel_settings()
            self.refresh_job = self.root.after(self.refresh_interval, self._start_channel_auto_refresh)

    def _stop_channel_auto_refresh(self):
        """Stop auto refresh timer for channels"""
        if self.refresh_job:
            self.root.after_cancel(self.refresh_job)
            self.refresh_job = None

    def _open_bitfield_editor(self, field_name, var, label):
        """Open a bitfield editor dialog"""
        BitfieldEditor(self.root, field_name, var, label)

    # Menu and shortcut methods
    def _focus_channel_settings(self):
        """Focus on the channel settings tab"""
        # Switch to channel settings tab
        self.notebook.select(self.tab_channels)
        # Focus on the first channel setting entry if available
        if self.channel_widgets:
            first_widget = next(iter(self.channel_widgets.values()))
            if 'entry' in first_widget:
                first_widget['entry'].focus_set()

    def _manual_refresh_all(self):
        """Manually refresh all settings"""
        self._refresh_view()
        self._load_channel_settings()

    def _load_all_settings(self):
        """Load all settings from device"""
        self._update_settings_display()
        self._load_channel_settings()

    def _show_shortcuts(self):
        """Show available keyboard shortcuts"""
        shortcuts_text = """
Keyboard Shortcuts:

Ctrl+S      - Focus Channel Settings Tab
Ctrl+`      - Toggle Command Line Interface  
F5          - Refresh All Settings
Ctrl+R      - Reload All Settings from Device

Channel Settings:
- Use the Channel dropdown to select different channels
- Toggle Auto Refresh to automatically update settings
- Apply individual settings or use "Apply All Changes"
- Use the bitfield editor for complex bit settings
        """
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)

    def _show_about(self):
        """Show about dialog"""
        about_text = """
MCS8 Measurement Control - Advanced

Version: 2.0
Enhanced UI with integrated Channel Settings

Features:
- Multi-channel configuration
- Real-time parameter updates  
- Advanced bitfield editing
- Command line interface
- Comprehensive device control

© 2024 MCS8 Control System
        """
        
        messagebox.showinfo("About", about_text)

    # Command line interface methods
    def _create_command_line_interface(self):
        """Create collapsible command line interface at the bottom of the window"""
        # Create main container frame
        self.cmd_container = ttk.Frame(self.root)
        self.cmd_container.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        # Create toggle frame with button
        toggle_frame = ttk.Frame(self.cmd_container)
        toggle_frame.pack(fill='x')
        
        # Toggle button with arrow
        self.cmd_visible = True
        self.toggle_btn = ttk.Button(
            toggle_frame, 
            text="▼ Hide Command Line Interface", 
            command=self._toggle_command_interface
        )
        self.toggle_btn.pack(side='left')
        
        # Add separator
        ttk.Separator(toggle_frame, orient='horizontal').pack(fill='x', expand=True, padx=10)
        
        # Create command line frame (initially visible)
        self.cmd_frame = ttk.Frame(self.cmd_container)
        self.cmd_frame.pack(fill='both', expand=True, pady=(5, 0))
        
        # Command input frame
        input_frame = ttk.Frame(self.cmd_frame)
        input_frame.pack(fill='x', pady=(0, 5))
        
        # Command prompt label
        ttk.Label(input_frame, text="MCS8>").pack(side='left', padx=(0, 5))
        
        # Command entry field
        self.command_entry = ttk.Entry(input_frame, font=('Consolas', 10))
        self.command_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        # Bind Enter key to execute command
        self.command_entry.bind('<Return>', self._execute_command)
        self.command_entry.bind('<Up>', self._history_up)
        self.command_entry.bind('<Down>', self._history_down)
        
        # Execute button
        execute_btn = ttk.Button(input_frame, text="Execute", command=self._execute_command)
        execute_btn.pack(side='right')
        
        # Clear button
        clear_btn = ttk.Button(input_frame, text="Clear Output", command=self._clear_command_output)
        clear_btn.pack(side='right', padx=(0, 5))
        
        # Output area with scrolling
        output_frame = ttk.Frame(self.cmd_frame)
        output_frame.pack(fill='both', expand=True)
        
        # Command output text area
        self.command_output = scrolledtext.ScrolledText(
            output_frame, 
            height=8,
            font=('Consolas', 9),
            bg='black',
            fg='lime',
            insertbackground='lime',
            wrap=tk.WORD,
            state='disabled'
        )
        self.command_output.pack(fill='both', expand=True)
        
        # Add tooltips
        CreateToolTip(self.command_entry, "Enter MCS8 commands here. Use Up/Down arrows for command history.")
        CreateToolTip(execute_btn, "Execute the command (or press Enter)")
        CreateToolTip(clear_btn, "Clear the command output area")
        CreateToolTip(self.toggle_btn, "Click to show/hide the command line interface (Ctrl+` shortcut)")
        
        # Initial welcome message
        self._append_to_output("MCS8 Advanced Command Line Interface\n")
        self._append_to_output("Type MCS8 commands and press Enter to execute.\n")
        self._append_to_output("Enhanced with integrated Channel Settings.\n")
        self._append_to_output("-" * 50 + "\n\n")

    def _toggle_command_interface(self):
        """Toggle the visibility of the command line interface"""
        if self.cmd_visible:
            # Hide the command interface
            self.cmd_frame.pack_forget()
            self.toggle_btn.config(text="▶ Show Command Line Interface")
            self.cmd_visible = False
            self.root.update_idletasks()
        else:
            # Show the command interface
            self.cmd_frame.pack(fill='both', expand=True, pady=(5, 0))
            self.toggle_btn.config(text="▼ Hide Command Line Interface")
            self.cmd_visible = True
            self.command_entry.focus_set()
            self.root.update_idletasks()

    def _execute_command(self, event=None):
        """Execute the command entered in the command line"""
        command = self.command_entry.get().strip()
        
        if not command:
            return
        
        # Add command to history
        if command not in self.command_history:
            self.command_history.append(command)
        
        # Reset history index
        self.history_index = -1
        
        # Display command in output
        self._append_to_output(f"MCS8> {command}\n")
        
        try:
            # Execute the command
            result = self.mcs.run_cmd(command)
            
            # Display result
            if result is not None:
                self._append_to_output(f"Result: {result}\n")
            else:
                self._append_to_output("Command executed successfully.\n")
                
            # If the command might have changed settings, update the displays
            if any(setting in command.lower() for setting in ['filename', 'board', 'dat', 'acq', 'range', 'dac', 'sweep']):
                self._update_settings_display()
                self._load_channel_settings()
                
        except Exception as e:
            self._append_to_output(f"Error: {str(e)}\n")
        
        self._append_to_output("\n")
        
        # Clear the command entry
        self.command_entry.delete(0, tk.END)
        
        # Auto-scroll to bottom
        self.command_output.see(tk.END)

    def _history_up(self, event):
        """Navigate up in command history"""
        if self.command_history:
            if self.history_index == -1:
                self.history_index = len(self.command_history) - 1
            elif self.history_index > 0:
                self.history_index -= 1
            
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[self.history_index])
        return 'break'  # Prevent default behavior

    def _history_down(self, event):
        """Navigate down in command history"""
        if self.command_history and self.history_index != -1:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.command_entry.delete(0, tk.END)
                self.command_entry.insert(0, self.command_history[self.history_index])
            else:
                self.history_index = -1
                self.command_entry.delete(0, tk.END)
        return 'break'  # Prevent default behavior

    def _append_to_output(self, text):
        """Append text to the command output area"""
        self.command_output.config(state='normal')
        self.command_output.insert(tk.END, text)
        self.command_output.config(state='disabled')
        
        # Limit output buffer size to prevent memory issues
        lines = self.command_output.get('1.0', tk.END).split('\n')
        if len(lines) > 500:  # Keep last 500 lines
            self.command_output.config(state='normal')
            self.command_output.delete('1.0', f'{len(lines)-400}.0')
            self.command_output.config(state='disabled')

    def _clear_command_output(self):
        """Clear the command output area"""
        self.command_output.config(state='normal')
        self.command_output.delete('1.0', tk.END)
        self.command_output.config(state='disabled')
        
        # Re-add welcome message
        self._append_to_output("Command output cleared.\n\n")

    # File handling methods
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
            if self.display:
                self.display.create_display()

    def _load_mpa(self):
        if self.filename:
            self.mcs.set_mpaname(self.filename)
            try:
                self.mcs.run_cmd(f"loadmpa {self.filename}")
                if self.display:
                    self.display.create_display()
            except Exception as e:
                print(f"Error loading MPA file: {e}")
                self._append_to_output(f"Error loading MPA file: {e}\n")

    # Settings application methods
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
            
            # If changing filename in DatSettings, update filename entry and MCS
            if 'dat' in settings_type and setting == 'filename':
                self.filename_entry.delete(0, tk.END)
                self.filename_entry.insert(0, value)
                self.filename = value
                self.mcs.set_mpaname(value)
            
            command = f"{setting}={value}"
            self.mcs.run_cmd(command)
            self._update_settings_display()
            
            # Log command to command line interface
            self._append_to_output(f"GUI Command: {command}\n")
            
        except Exception as e:
            print(f"Error applying setting: {e}")
            self._append_to_output(f"GUI Error: {str(e)}\n")

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
                value = getattr(dat, key, None)
                if value is not None:
                    self.dat_settings[key]['value'].set(str(value))
            
            # Update board settings
            for key in self.board_settings:
                value = getattr(board, key)
                if key == 'sweepmode':
                    value = f"{value:08x}"
                self.board_settings[key]['value'].set(str(value))
                
        except Exception as e:
            print(f"Error updating settings display: {e}")
            self._append_to_output(f"Settings Update Error: {str(e)}\n")

    # Timer and refresh methods
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

        except Exception as e:
            print(f"Error in refresh: {e}")

    def _on_tab_changed(self, event):
        # Get the newly selected tab
        current_tab = self.notebook.select()
        # Get the tab index of the display tab (last tab)
        display_tab = self.notebook.tabs()[-1]
        channel_tab = str(self.tab_channels)
        
        # Only update if we are switching TO the display tab
        if current_tab == display_tab and hasattr(self, '_last_tab') and self.notebook.select() != self._last_tab:
            if self.display:
                self.display.update_plot()
        
        # Auto-load channel settings when switching to channel tab
        if current_tab == channel_tab and hasattr(self, '_last_tab') and self._last_tab != channel_tab:
            self._load_channel_settings()
        
        # Store the current tab for next comparison
        self._last_tab = current_tab

    def _setup_display(self):
        """Setup the display tab with plot and refresh controls"""
        # Initialize display instance
        self.display = MCSDisplay(self.tab_display, self.mcs)
        
        # Create control frame
        control_frame = ttk.Frame(self.tab_display)
        control_frame.pack(fill='x', side='top', padx=5, pady=5)
        
        # Add performance options
        perf_frame = ttk.LabelFrame(control_frame, text="Performance Options")
        perf_frame.pack(side='left', padx=5)
        
        # Update interval control
        ttk.Label(perf_frame, text="Update Interval (ms):").pack(side='left', padx=5)
        interval_var = tk.IntVar(value=self.display_update_interval)
        interval_spin = ttk.Spinbox(
            perf_frame, 
            from_=100, 
            to=5000, 
            increment=100,
            textvariable=interval_var,
            width=10,
            command=lambda: setattr(self, 'display_update_interval', interval_var.get())
        )
        interval_spin.pack(side='left', padx=5)
        
        # Add manual refresh button
        refresh_btn = ttk.Button(
            control_frame,
            text="Refresh Now",
            command=lambda: self.display.update_plot() if self.display else None
        )
        refresh_btn.pack(side='left', padx=10)


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