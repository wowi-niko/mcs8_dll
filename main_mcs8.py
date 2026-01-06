# mcs_ui.py
"""
Main MCS8 User Interface module.
Provides the primary GUI interface for MCS8 device control.
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from mcs8_func import MCS8, CreateToolTip
from plot_display import extend_mcs_display
from structures import ACQSETTING, DATSETTING, BOARDSETTING
from settings_manager import SettingsManager

REFRESH_RATE = 4000  # ms


class MCSUI:
    """Enhanced MCS8 User Interface with integrated Channel Settings"""

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
        
        # Initialize settings manager
        self.settings_manager = SettingsManager(self.mcs, self._append_to_output)
        
        # File handling
        self.filename = None
        
        self._setup_ui()
        self.check_DLL()
        
        # Set initial window size
        self.root.geometry("1000x800")
        self.root.update_idletasks()

    def refresh_settings(self):
        self.acq = self.mcs.get_acq_setting(0)
        self.dat = self.mcs.get_dat_setting()
        self.board = self.mcs.get_mcs_setting()
        
    def check_DLL(self):
        """Check DLL status and show warning if needed"""
        if (self.mcs.check_status() == 0 and not self.dl_warning_shown):
            self.dl_warning_shown = True
            messagebox.showwarning("No DLL active!", "MCS8 not connected. Please start the DLL first.")
            
    def _setup_ui(self):
        """Setup the complete user interface"""
        self._setup_window()
        self._create_menu_bar()
        self._create_controls()
        self._create_notebook()
        self._setup_display()
        self._create_command_line_interface()
        self._start_refresh_timer()

    def _setup_window(self):
        """Setup main window properties and keyboard shortcuts"""
        self.root.title("MCS8 Python DLL - FAST ComTec GmbH")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)
        
        # Keyboard shortcuts
        self.root.bind('<Control-quoteleft>', lambda e: self._toggle_command_interface())
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

    def _create_controls(self):
        """Create main control buttons and file handling widgets"""
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=0, column=0, sticky="ew")

        # Control buttons - Row 0
        control_buttons = [
            ("▶", "Start Measurement", self._start),
            ("■", "Stop Measurement", self._stop),
            ("⏵", "Continue Measurement", self._continue),
            ("⌫", "Erase Data", self._erase)
        ]
        
        for i, (text, tooltip, command) in enumerate(control_buttons):
            btn = ttk.Button(button_frame, text=text, command=command)
            btn.grid(row=0, column=i, padx=5)
            CreateToolTip(btn, tooltip)

        # Filename controls - Row 1
        self._create_filename_controls(button_frame)

    def _create_filename_controls(self, parent):
        """Create filename handling controls"""
        filename_frame = ttk.Frame(parent)
        filename_frame.grid(row=1, column=0, columnspan=5, pady=5)

        ttk.Label(filename_frame, text="MPA Filename:").pack(side=tk.LEFT, padx=5)
        
        self.filename_entry = ttk.Entry(filename_frame, width=40)
        self.filename_entry.pack(side=tk.LEFT, padx=5)
        self.filename_entry.bind("<FocusOut>", self._update_filename)
        
        file_buttons = [
            ("Set Filename", self._set_filename_from_entry),
            ("Browse", self._browse_file),
            ("Load MPA", self._load_mpa),
            ("Save Config", self.mcs.save_cnf),
            ("Save MPA", self.mcs.savempa)
        ]
        
        for text, command in file_buttons:
            ttk.Button(filename_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)

    def _create_notebook(self):
        """Create main notebook with tabs"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Create tabs
        self.tab_status = ttk.Frame(self.notebook)
        self.tab_acq = ttk.Frame(self.notebook)
        self.tab_dat = ttk.Frame(self.notebook)
        self.tab_board = ttk.Frame(self.notebook)
        self.tab_channels = ttk.Frame(self.notebook)
        self.tab_display = ttk.Frame(self.notebook)

        # Add tabs to notebook
        tab_configs = [
            (self.tab_status, "AcqStatus"),
            (self.tab_acq, "AcqSettings"),
            (self.tab_dat, "DatSettings"),
            (self.tab_board, "BoardSettings"),
            (self.tab_channels, "Channel Settings"),
            (self.tab_display, "DataDisplay")
        ]
        
        for tab, text in tab_configs:
            self.notebook.add(tab, text=text)

        # Create settings tabs using settings manager
        self._create_settings_tabs()
        
        # Create channel settings tab
        self.settings_manager.create_channel_settings_tab(self.tab_channels)
        
        # Bind tab changed event
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        # Status tab
        self.status_label = ttk.Label(
            self.tab_status, text="", relief="sunken", 
            padding="5", anchor="nw", justify="left"
        )
        self.status_label.pack(expand=True, fill="both", padx=5, pady=5)

    def _create_settings_tabs(self):
        """Create settings tabs using the settings manager"""
        settings_configs = [
            (self.tab_acq, ACQSETTING, "Acquisition Settings"),
            (self.tab_dat, DATSETTING, "Data Settings"),
            (self.tab_board, BOARDSETTING, "Board Settings")
        ]
        
        for tab, settings_class, title in settings_configs:
            settings_dict, status_label = self.settings_manager.create_settings_tab(
                tab, settings_class, title
            )
            
            # Store references for updating
            setattr(self, f"{title.lower().replace(' ', '_').replace('_settings', '')}_settings", settings_dict)
            self.status_labels[title] = status_label
            
            # Store settings in manager for apply_setting method
            self.settings_manager.settings_data[title.lower().replace(' settings', '')] = settings_dict


    # Control methods
    def _start(self):
        """Start data acquisition with display refresh"""
        self.refresh_settings()

        if self.display:
            self.display._clear_display()
        self.mcs.start()
        if self.display:
            self.root.after(500, lambda: self.display.create_display())
            self.display.start_live_updates()

    def _stop(self):
        """Stop data acquisition with display refresh"""
        self._isplaying = False
        self.mcs.halt()
        self.display.stop_live_updates()

    def _continue(self):
        """Continue data acquisition with display refresh"""
        self._isplaying = True
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

    # File handling methods
    def _update_filename(self, event):
        """Update filename from entry widget"""
        text = event.widget.get()
        self.filename = text

    def _set_filename_from_entry(self):
        """Set the filename in the MCS device from the entry field"""
        filename = self.filename_entry.get()
        if filename:
            self.filename = filename
            self.mcs.set_mpaname(filename)

    def _browse_file(self):
        """Browse and select MPA file"""
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
        """Load MPA file"""
        if self.filename:
            self.mcs.set_mpaname(self.filename)
            try:
                self.mcs.run_cmd(f"loadmpa {self.filename}")
                if self.display:
                    self.display.create_display()
            except Exception as e:
                print(f"Error loading MPA file: {e}")
                self._append_to_output(f"Error loading MPA file: {e}\n")

    # Display setup
    def _setup_display(self):
        """Setup the display tab with plot and refresh controls"""
        EfficientMCSDisplay = extend_mcs_display()
        self.display = EfficientMCSDisplay(self.tab_display, self.mcs)
        self.display.start_live_updates()

        
        # Create control frame
        control_frame = ttk.Frame(self.tab_display)
        control_frame.pack(fill='x', side='top', padx=5, pady=5)
        
        # Manual refresh button
        refresh_btn = ttk.Button(
            control_frame,
            text="Refresh Now",
            command=lambda: self.display.update_plot() if self.display else None
        )
        refresh_btn.pack(side='left', padx=10)

    # Command line interface
    def _create_command_line_interface(self):
        """Create collapsible command line interface"""
        # Main container
        self.cmd_container = ttk.Frame(self.root)
        self.cmd_container.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        # Toggle frame
        toggle_frame = ttk.Frame(self.cmd_container)
        toggle_frame.pack(fill='x')
        
        # Toggle button
        self.cmd_visible = True
        self.toggle_btn = ttk.Button(
            toggle_frame, 
            text="▼ Hide Command Line Interface", 
            command=self._toggle_command_interface
        )
        self.toggle_btn.pack(side='left')
        
        # Separator
        ttk.Separator(toggle_frame, orient='horizontal').pack(fill='x', expand=True, padx=10)
        
        # Command frame
        self.cmd_frame = ttk.Frame(self.cmd_container)
        self.cmd_frame.pack(fill='both', expand=True, pady=(5, 0))
        
        self._create_command_input()
        self._create_command_output()
        
        # Initial welcome message
        welcome_messages = [
            "MCS8 Advanced Command Line Interface\n",
            "Type MCS8 commands and press Enter to execute.\n",
            "Enhanced with integrated Channel Settings.\n",
            "-" * 50 + "\n\n"
        ]
        
        for msg in welcome_messages:
            self._append_to_output(msg)

    def _create_command_input(self):
        """Create command input area"""
        input_frame = ttk.Frame(self.cmd_frame)
        input_frame.pack(fill='x', pady=(0, 5))
        
        # Command prompt
        ttk.Label(input_frame, text="MCS8>").pack(side='left', padx=(0, 5))
        
        # Command entry
        self.command_entry = ttk.Entry(input_frame, font=('Consolas', 10))
        self.command_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        # Bind events
        self.command_entry.bind('<Return>', self._execute_command)
        self.command_entry.bind('<Up>', self._history_up)
        self.command_entry.bind('<Down>', self._history_down)
        
        # Buttons
        ttk.Button(input_frame, text="Execute", command=self._execute_command).pack(side='right')
        ttk.Button(input_frame, text="Clear Output", command=self._clear_command_output).pack(side='right', padx=(0, 5))
        
        # Tooltips
        CreateToolTip(self.command_entry, "Enter MCS8 commands here. Use Up/Down arrows for command history.")

    def _create_command_output(self):
        """Create command output area"""
        output_frame = ttk.Frame(self.cmd_frame)
        output_frame.pack(fill='both', expand=True)
        
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

    def _toggle_command_interface(self):
        """Toggle the visibility of the command line interface"""
        if self.cmd_visible:
            self.cmd_frame.pack_forget()
            self.toggle_btn.config(text="▶ Show Command Line Interface")
            self.cmd_visible = False
        else:
            self.cmd_frame.pack(fill='both', expand=True, pady=(5, 0))
            self.toggle_btn.config(text="▼ Hide Command Line Interface")
            self.cmd_visible = True
            self.command_entry.focus_set()
        self.root.update_idletasks()

    def _execute_command(self, event=None):
        """Execute command entered in the command line"""
        command = self.command_entry.get().strip()
        
        if not command:
            return
        
        # Add to history
        if command not in self.command_history:
            self.command_history.append(command)
        
        self.history_index = -1
        
        # Display command
        self._append_to_output(f"MCS8> {command}\n")
        
        try:
            result = self.mcs.run_cmd(command)
            
            if result is not None:
                self._append_to_output(f"Result: {result}\n")
            else:
                self._append_to_output("Command executed successfully.\n")
                
            # Update displays if needed
            if any(setting in command.lower() for setting in 
                   ['filename', 'board', 'dat', 'acq', 'range', 'dac', 'sweep']):
                #self._update_settings_display()
                self.settings_manager.load_channel_settings()
                
        except Exception as e:
            self._append_to_output(f"Error: {str(e)}\n")
        
        self._append_to_output("\n")
        self.command_entry.delete(0, tk.END)
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
        return 'break'

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
        return 'break'

    def _append_to_output(self, text):
        """Append text to command output area"""
        self.command_output.config(state='normal')
        self.command_output.insert(tk.END, text)
        self.command_output.config(state='disabled')
        
        # Limit buffer size
        lines = self.command_output.get('1.0', tk.END).split('\n')
        if len(lines) > 500:
            self.command_output.config(state='normal')
            self.command_output.delete('1.0', f'{len(lines)-400}.0')
            self.command_output.config(state='disabled')

    def _clear_command_output(self):
        """Clear command output area"""
        self.command_output.config(state='normal')
        self.command_output.delete('1.0', tk.END)
        self.command_output.config(state='disabled')
        self._append_to_output("Command output cleared.\n\n")

    # Settings and refresh methods
    def _update_settings_display(self):
        """Update all settings displays with current values"""
        try:
            # Update traditional settings
            self.settings_manager.update_settings_display(
                self.acq_settings, lambda: self.mcs.get_acq_setting()
            )
            self.settings_manager.update_settings_display(
                self.dat_settings, lambda: self.mcs.get_dat_setting()
            )
            self.settings_manager.update_settings_display(
                self.board_settings, lambda: self.mcs.get_mcs_setting()
            )
                
        except Exception as e:
            print(f"Error updating settings display: {e}")
            self._append_to_output(f"Settings Update Error: {str(e)}\n")

    def _start_refresh_timer(self):
        """Start the refresh timer"""
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
            display_tab = self.notebook.tabs()[-1]
            
            if current_tab != display_tab:
                status = self.mcs.get_status()
                acq = self.mcs.get_acq_setting()
                dat = self.mcs.get_dat_setting()
                board = self.mcs.get_mcs_setting()

                # Update status displays
                self.status_label.config(text=MCS8.status_text(status))
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
        """Handle tab change events"""
        current_tab = self.notebook.select()
        display_tab = self.notebook.tabs()[-1]
        channel_tab = str(self.tab_channels)
        
        # Update display if switching to display tab
        if (current_tab == display_tab and hasattr(self, '_last_tab') and 
            self.notebook.select() != self._last_tab):
            if self.display:
                self.display.update_plot()
        
        # Auto-load channel settings when switching to channel tab
        if (current_tab == channel_tab and hasattr(self, '_last_tab') and 
            self._last_tab != channel_tab):
            self.settings_manager.load_channel_settings()
        
        self._last_tab = current_tab

    # Menu and shortcut methods
    def _focus_channel_settings(self):
        """Focus on the channel settings tab"""
        self.notebook.select(self.tab_channels)
        # Focus on first available entry widget
        for widget_info in self.settings_manager.channel_widgets.values():
            if 'entry' in widget_info:
                widget_info['entry'].focus_set()
                break

    def _manual_refresh_all(self):
        """Manually refresh all settings"""
        self._refresh_view()
        self.settings_manager.load_channel_settings()

    def _load_all_settings(self):
        """Load all settings from device"""
        #self._update_settings_display()
        self.settings_manager.load_channel_settings()

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


def main_cmd():
    """Run command line interface"""
    mcs = MCS8()
    mcs.run_command_loop()


def main_ui():
    """Run GUI interface"""
    mcs = MCS8()
    ui = MCSUI(mcs)
    ui.root.mainloop()


if __name__ == '__main__':
    main_ui()
