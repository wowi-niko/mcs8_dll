# --- Imports ---
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from mcs8_func import MCS8, CreateToolTip
from plot_display import MCSDisplay
from structures import *

REFRESH_RATE = 4000 # ms


class MCSUI:

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
        
        self._setup_ui()
        self.filename = None
        self.check_DLL()
        
        # Set initial window size
        self.root.geometry("1000x800")
        self.root.update_idletasks()
        

    def check_DLL(self):
        if (self.mcs.check_status() == 0 and self.dl_warning_shown == False):
            self.dl_warning_shown = True
            messagebox.showwarning("No DLL active!", "MCS8 not connected. Please start the DLL first.")
            
    
    def _setup_ui(self):
        self._setup_window()
        self._create_controls()
        self._create_notebook()
        self._setup_display()
        self._create_command_line_interface()  # Add command line interface
        self._start_refresh_timer()

    def _setup_window(self):
        self.root.title("MCS8 Measurement Control")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        # Add weight for command line interface row
        self.root.rowconfigure(2, weight=0)
        
        # Add keyboard shortcut for toggling command line (Ctrl+`)
        self.root.bind('<Control-grave>', lambda e: self._toggle_command_interface())
        
        self._set_window_icon()
    
    def _set_window_icon(self):
        """Set the window icon with fallback options"""
        icon_paths = [
            'fast.ico',
        ]
        
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
                # Keep reference to prevent garbage collection
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

        # Create and configure buttons with tooltips
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

        filename_frame = ttk.Frame(button_frame)
        filename_frame.grid(row=1, column=0, columnspan=5, pady=5)

        ttk.Label(filename_frame, text="MPA Filename:").pack(side=tk.LEFT, padx=5)
        self.filename_entry = ttk.Entry(filename_frame, width=40)
        self.filename_entry.pack(side=tk.LEFT, padx=5)
        
        # update filename if entry is changed
        self.filename_entry.bind("<FocusOut>", self.update_filename)
        
        # Add Set Filename button
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
            self.root.after(1000, lambda: self.display.create_display())  # Delay to allow data collection

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
        self._append_to_output("MCS8 Command Line Interface\n")
        self._append_to_output("Type MCS8 commands and press Enter to execute.\n")
        self._append_to_output("-" * 50 + "\n\n")

    def _toggle_command_interface(self):
        """Toggle the visibility of the command line interface"""
        if self.cmd_visible:
            # Hide the command interface
            self.cmd_frame.pack_forget()
            self.toggle_btn.config(text="▶ Show Command Line Interface")
            self.cmd_visible = False
            # Adjust window size to reclaim space
            self.root.update_idletasks()
        else:
            # Show the command interface
            self.cmd_frame.pack(fill='both', expand=True, pady=(5, 0))
            self.toggle_btn.config(text="▼ Hide Command Line Interface")
            self.cmd_visible = True
            # Focus on command entry when shown
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
            if any(setting in command.lower() for setting in ['filename', 'board', 'dat', 'acq', 'range']):
                self._update_settings_display()
                
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
        
        # Only update if we are switching TO the display tab
        if current_tab == display_tab and hasattr(self, '_last_tab') and self.notebook.select() != self._last_tab:
            if self.display:
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