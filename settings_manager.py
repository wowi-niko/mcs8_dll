# settings_manager.py
"""
Settings management module for MCS8 control interface.
Handles channel settings, bitfield editing, and configuration management.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from structures import ACQSETTING, DATSETTING, BOARDSETTING
from mcs8_func import CreateToolTip


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


class SettingsManager:
    """Manages all settings-related functionality for the MCS8 interface"""
    
    def __init__(self, mcs, output_callback=None):
        self.mcs = mcs
        self.output_callback = output_callback or (lambda x: None)
        
        # Channel settings state
        self.current_channel = 0
        self.max_channels = 8
        self.modified_settings = set()
        self.channel_widgets = {}
        
        # Command mappings
        self.command_mapping = {
            'range': 'range', 'roimin': 'roimin', 'roimax': 'roimax',
            'eventpreset': 'eventpreset', 'bitshift': 'bitshift', 'active': 'active',
            'sweepmode': 'sweepmode', 'prena': 'prena', 'cycles': 'cycles',
            'sequences': 'sequences', 'swpreset': 'swpreset', 'timepreset': 'rtpreset',
            'holdafter': 'holdafter', 'fstchan': 'fstchan', 'tagbits': 'tagbits',
            'periods': 'periods', 'digio': 'digio', 'syncout': 'syncout',
            'dac0': 'dac0v', 'dac1': 'dac1v', 'dac2': 'dac2v',
            'dac3': 'dac3v', 'dac4': 'dac4v', 'dac5': 'dac5v',
            'dac6': 'dac6v', 'dac7': 'dac7v',
            'savedata': 'savedata', 'autoinc': 'autoinc', 'fmt': 'fmt',
            'mpafmt': 'mpafmt', 'sephead': 'sephead'
        }
        
        self.voltage_dac_mapping = {
            f'dac{i}': f'dac{i}v' for i in range(6)
        }
        
        # Settings data structures
        self.settings_data = {}
        
    def create_settings_tab(self, tab, settings_class, title):
        """Create a settings tab with status display and scrollable settings"""
        main_frame = ttk.Frame(tab)
        main_frame.pack(expand=True, fill="both")
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Current Status")
        status_frame.pack(fill='x', padx=5, pady=5)
        
        status_label = ttk.Label(status_frame, text="", relief="sunken", 
                               padding="5", anchor="nw", justify="left")
        status_label.pack(expand=True, fill="both", padx=5, pady=5)
        
        # Settings frame with scrolling
        settings_frame = self._create_scrollable_frame(main_frame)
        
        # Create settings dictionary and widgets
        settings_dict = self._create_settings_widgets(settings_frame, settings_class, title)
        
        return settings_dict, status_label
        
    def _create_scrollable_frame(self, parent):
        """Create a scrollable frame for settings"""
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(expand=True, fill="both", padx=5, pady=5)

        canvas = tk.Canvas(settings_frame)
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        return scrollable_frame
    
    def _create_settings_widgets(self, parent, settings_class, title):
        """Create settings widgets for a given settings class"""
        settings_dict = {}
        
        # Header
        header = ttk.Label(parent, text=f"{title} Configuration", 
                          font=('TkDefaultFont', 10, 'bold'))
        header.pack(fill='x', padx=5, pady=5)

        # Create widgets for each setting
        for field_name, meta in settings_class.settings_meta.items():
            settings_dict[field_name] = {
                'label': meta['label'],
                'value': tk.StringVar(value=str(meta['default'])),
                'tooltip': meta['tooltip']
            }
            
            self._create_setting_widget(parent, field_name, settings_dict[field_name], title)
            
        return settings_dict
    
    def _create_setting_widget(self, parent, field_name, setting_data, title):
        """Create a single setting widget"""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=2)

        # Label
        label = ttk.Label(frame, text=f"{setting_data['label']}:", width=20, anchor='e')
        label.pack(side='left', padx=5)

        # Entry
        entry = ttk.Entry(frame, textvariable=setting_data['value'])
        entry.pack(side='left', fill='x', expand=True, padx=5)
        
        # Apply button
        apply_btn = ttk.Button(frame, text="Apply", 
                             command=lambda: self.apply_setting(field_name, title.lower()))
        apply_btn.pack(side='right', padx=5)
        
        # Tooltip
        CreateToolTip(entry, setting_data['tooltip'])
        
        return frame
    
    def create_channel_settings_tab(self, parent):
        """Create the integrated channel settings tab"""
        # Store parent reference
        self.channel_parent = parent
        
        # Main container
        main_container = ttk.Frame(parent)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Control frame
        self._create_channel_controls(main_container)
        
        # Settings notebook
        self.channel_notebook = ttk.Notebook(main_container)
        self.channel_notebook.pack(fill='both', expand=True)
        
        # Create setting category tabs
        self._create_channel_setting_tabs()
        
        # Action buttons
        self._create_channel_action_buttons(main_container)
        
        return main_container
    
    def _create_channel_controls(self, parent):
        """Create channel control widgets"""
        control_frame = ttk.LabelFrame(parent, text="Channel Control")
        control_frame.pack(fill='x', pady=(0, 5))
        
        top_controls = ttk.Frame(control_frame)
        top_controls.pack(fill='x', padx=10, pady=5)
        
        # Channel selector
        ttk.Label(top_controls, text="Channel:").pack(side='left')
        self.channel_var = tk.IntVar(value=self.current_channel)
        channel_combo = ttk.Combobox(
            top_controls, textvariable=self.channel_var,
            values=list(range(self.max_channels)), state='readonly', width=5
        )
        channel_combo.pack(side='left', padx=5)
        channel_combo.bind('<<ComboboxSelected>>', self._on_channel_change)
        
        # Auto refresh
        self.auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top_controls, text="Auto Refresh", 
                       variable=self.auto_refresh_var).pack(side='left', padx=20)
        
        # Manual refresh
        ttk.Button(top_controls, text="Refresh Now", 
                  command=self.load_channel_settings).pack(side='left', padx=5)
        
        # Status indicator
        self.channel_status_label = ttk.Label(top_controls, text="Ready", foreground="green")
        self.channel_status_label.pack(side='right', padx=10)
    
    def _create_channel_setting_tabs(self):
        """Create tabs for different channel setting categories"""
        tab_configs = [
            ("Acquisition", self._create_acquisition_settings),
            ("Timing", self._create_timing_settings),
            ("DAC/Voltages", self._create_dac_settings),
            ("Advanced", self._create_advanced_settings),
            ("Data", self._create_data_settings)
        ]
        
        for name, creator_func in tab_configs:
            tab = ttk.Frame(self.channel_notebook)
            self.channel_notebook.add(tab, text=name)
            creator_func(tab)
    
    def _create_acquisition_settings(self, parent):
        """Create acquisition settings widgets"""
        scrollable_frame = self._create_scrollable_frame(parent)
        
        acq_frame = ttk.LabelFrame(scrollable_frame, text="Spectrum Configuration")
        acq_frame.pack(fill='x', padx=5, pady=5)
        
        settings = [
            ('range', 'Spectrum Length'),
            ('roimin', 'ROI Minimum'),
            ('roimax', 'ROI Maximum'),
            ('eventpreset', 'Event Preset'),
            ('bitshift', 'Bit Shift'),
            ('active', 'Active Mode')
        ]
        
        for field_name, label in settings:
            self._create_channel_setting_widget(acq_frame, field_name, ACQSETTING, label)
    
    def _create_timing_settings(self, parent):
        """Create timing settings widgets"""
        # Preset settings
        preset_frame = ttk.LabelFrame(parent, text="Preset Configuration")
        preset_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(preset_frame, 'prena', BOARDSETTING, 
                                          'Preset Enable', widget_type='bitfield')
        
        # Timing values
        timing_frame = ttk.LabelFrame(parent, text="Timing Values")
        timing_frame.pack(fill='x', padx=5, pady=5)
        
        timing_settings = [
            ('swpreset', 'Sweep Preset'),
            ('timepreset', 'Time Preset (s)'),
            ('holdafter', 'Hold After'),
            ('fstchan', 'First Channel Delay')
        ]
        
        for field_name, label in timing_settings:
            self._create_channel_setting_widget(timing_frame, field_name, BOARDSETTING, label)
        
        # Sequential mode
        seq_frame = ttk.LabelFrame(parent, text="Sequential Mode")
        seq_frame.pack(fill='x', padx=5, pady=5)
        
        seq_settings = [
            ('cycles', 'Cycles'),
            ('sequences', 'Sequences'),
            ('periods', 'Periods')
        ]
        
        for field_name, label in seq_settings:
            self._create_channel_setting_widget(seq_frame, field_name, BOARDSETTING, label)
    
    def _create_dac_settings(self, parent):
        """Create DAC/voltage settings widgets"""
        # Voltage settings
        voltage_frame = ttk.LabelFrame(parent, text="DAC Voltage Settings")
        voltage_frame.pack(fill='x', padx=5, pady=5)
        
        for i in range(6):
            dac_name = f'dac{i}'
            label = f'DAC{i} Voltage' + (' (START)' if i == 0 else f' (STOP{i})')
            self._create_voltage_widget(voltage_frame, dac_name, label)
        
        # Hex DAC values
        hex_frame = ttk.LabelFrame(parent, text="DAC Hex Values")
        hex_frame.pack(fill='x', padx=5, pady=5)
        
        for i in range(6):
            dac_name = f'dac{i}'
            label = f'DAC{i} Hex Value'
            self._create_channel_setting_widget(hex_frame, dac_name, BOARDSETTING, label, widget_type='hex')
    
    def _create_advanced_settings(self, parent):
        """Create advanced settings widgets"""
        # Sweep mode
        mode_frame = ttk.LabelFrame(parent, text="Sweep Mode Configuration")
        mode_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(mode_frame, 'sweepmode', BOARDSETTING, 
                                          'Sweep Mode', widget_type='hex')
        
        # Digital I/O
        dio_frame = ttk.LabelFrame(parent, text="Digital I/O Configuration")
        dio_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(dio_frame, 'digio', BOARDSETTING, 
                                          'Digital I/O', widget_type='bitfield')
        self._create_channel_setting_widget(dio_frame, 'syncout', BOARDSETTING, 'Sync Output')
        
        # Advanced settings
        advanced_frame = ttk.LabelFrame(parent, text="Advanced Configuration")
        advanced_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_channel_setting_widget(advanced_frame, 'tagbits', BOARDSETTING, 'Tag Bits')
    
    def _create_data_settings(self, parent):
        """Create data settings widgets"""
        format_frame = ttk.LabelFrame(parent, text="Data Format")
        format_frame.pack(fill='x', padx=5, pady=5)
        
        data_settings = [
            ('savedata', 'Save Data Mode'),
            ('autoinc', 'Auto Increment'),
            ('fmt', 'Format Type'),
            ('mpafmt', 'MPA Format'),
            ('sephead', 'Separate Header')
        ]
        
        for field_name, label in data_settings:
            self._create_channel_setting_widget(format_frame, field_name, DATSETTING, label)
    
    def _create_channel_setting_widget(self, parent, field_name, structure_class, label, widget_type='entry'):
        """Create a channel setting widget with label, entry, and apply button"""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=2)
        
        # Label
        ttk.Label(frame, text=f"{label}:", width=20, anchor='e').pack(side='left', padx=5)
        
        # Get metadata
        meta = getattr(structure_class, 'settings_meta', {}).get(field_name, {})
        tooltip = meta.get('tooltip', f'Set {label}')
        
        # Value variable
        var = tk.StringVar()
        var.trace('w', lambda *args, fn=field_name: self._mark_modified(fn))
        
        # Create entry widget
        entry = ttk.Entry(frame, textvariable=var, width=15)
        entry.pack(side='left', padx=5)
        
        # Add special widgets for bitfields
        if widget_type == 'bitfield':
            ttk.Button(frame, text="Edit Bits", 
                      command=lambda: self._open_bitfield_editor(field_name, var, label)).pack(side='left', padx=2)
        
        # Status indicator
        status_label = ttk.Label(frame, text="●", foreground="green", width=2)
        status_label.pack(side='left')
        
        # Apply button
        ttk.Button(frame, text="Apply", 
                  command=lambda: self.apply_channel_setting(field_name, var.get(), status_label)).pack(side='right', padx=5)
        
        # Store widget references
        self.channel_widgets[field_name] = {
            'var': var, 'entry': entry, 'status': status_label,
            'structure': structure_class, 'meta': meta
        }
        
        CreateToolTip(entry, tooltip)
    
    def _create_voltage_widget(self, parent, dac_name, label):
        """Create a voltage setting widget with adjustment buttons"""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(frame, text=f"{label}:", width=20, anchor='e').pack(side='left', padx=5)
        
        # Voltage controls
        ttk.Button(frame, text="-", width=3,
                  command=lambda: self._adjust_voltage(dac_name, -0.001)).pack(side='left', padx=2)
        
        var = tk.StringVar(value="0.000")
        entry = ttk.Entry(frame, textvariable=var, width=10, justify='center')
        entry.pack(side='left', padx=2)
        
        ttk.Button(frame, text="+", width=3,
                  command=lambda: self._adjust_voltage(dac_name, 0.001)).pack(side='left', padx=2)
        
        ttk.Button(frame, text="Set Voltage",
                  command=lambda: self.apply_voltage(dac_name, var.get())).pack(side='right', padx=5)
        
        self.channel_widgets[f'{dac_name}_voltage'] = {'var': var, 'entry': entry}
        CreateToolTip(entry, f"Set {label} in Volts")
    
    def _create_channel_action_buttons(self, parent):
        """Create action buttons for channel settings"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=(5, 0))
        
        # Left side buttons
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side='left')
        
        ttk.Button(left_frame, text="Load All Settings", 
                  command=self.load_channel_settings).pack(side='left', padx=5)
        ttk.Button(left_frame, text="Save Config", 
                  command=self.mcs.save_cnf).pack(side='left', padx=5)
        
        # Right side buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side='right')
        
        ttk.Button(right_frame, text="Apply All Changes", 
                  command=self.apply_all_changes).pack(side='left', padx=5)
        ttk.Button(right_frame, text="Reset Changes", 
                  command=self.reset_changes).pack(side='left', padx=5)
    
    # Settings application methods
    def apply_setting(self, setting, settings_type):
        """Apply a setting to the device"""
        try:
            settings_dict = self.settings_data.get(settings_type, {})
            if setting not in settings_dict:
                raise ValueError(f"Setting {setting} not found in {settings_type}")
            
            value = settings_dict[setting]['value'].get()
            
            # Handle special cases
            if setting == 'sweepmode' and not value.startswith('0x'):
                value = f"0x{value}"
            
            command = f"{setting}={value}"
            self.mcs.run_cmd(command)
            
            self.output_callback(f"GUI Command: {command}\n")
            
        except Exception as e:
            self.output_callback(f"GUI Error: {str(e)}\n")
            raise
    
    def apply_channel_setting(self, field_name, value, status_label):
        """Apply a single channel setting"""
        try:
            command_name = self.command_mapping.get(field_name)
            if not command_name:
                raise ValueError(f"No command mapping for {field_name}")
            
            # Format value
            if field_name == 'sweepmode' and not value.startswith('0x'):
                value = f"0x{value}"
            
            if 'dac' in field_name:
                value = f'{((float(value) - 2048) / 1000):.3f}'
                voltage_widget = self.channel_widgets.get(f'{field_name}_voltage')
                if voltage_widget:
                    voltage_widget['var'].set(value)
            
            # Send command
            command = f"{command_name}={value}"
            self.mcs.run_cmd(command)
            
            # Update status
            status_label.config(foreground="green")
            self.modified_settings.discard(field_name)
            
            self._update_status(f"Applied: {command}", "green")
            self.output_callback(f"Channel Command: {command}\n")
            
        except Exception as e:
            status_label.config(foreground="red")
            self._update_status(f"Error: {e}", "red")
            messagebox.showerror("Error", f"Failed to apply {field_name}: {e}")
    
    def apply_voltage(self, dac_name, voltage_str):
        """Apply voltage setting to DAC"""
        try:
            voltage = float(voltage_str)
            command_name = self.voltage_dac_mapping.get(dac_name)
            if not command_name:
                raise ValueError(f"No voltage command mapping for {dac_name}")
            
            command = f"{command_name}={voltage:.3f}"
            self.mcs.run_cmd(command)
            
            self._update_status(f"Applied: {command}", "green")
            self.output_callback(f"Voltage Command: {command}\n")
            
        except Exception as e:
            self._update_status(f"Error: {e}", "red")
            messagebox.showerror("Error", f"Failed to set voltage: {e}")
    
    def apply_all_changes(self):
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
                    self.apply_channel_setting(field_name, value, widget_info['status'])
                    applied_count += 1
            
            messagebox.showinfo("Success", f"Applied {applied_count} changes")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error applying changes: {e}")
    
    def reset_changes(self):
        """Reset all changes and reload from device"""
        if self.modified_settings:
            if messagebox.askyesno("Confirm Reset", "Discard all unsaved changes?"):
                self.load_channel_settings()
    
    def load_channel_settings(self):
        """Load current channel settings from device"""
        try:
            self._update_status("Loading settings...", "orange")
            
            # Get current settings
            acq = self.mcs.get_acq_setting(self.current_channel)
            dat = self.mcs.get_dat_setting()
            board = self.mcs.get_mcs_setting()
            
            # Update widgets
            for field_name, widget_info in self.channel_widgets.items():
                if field_name.endswith('_voltage'):
                    continue
                    
                structure = widget_info['structure']
                value = None
                
                if structure == ACQSETTING:
                    value = getattr(acq, field_name, '')
                elif structure == DATSETTING:
                    value = getattr(dat, field_name, '')
                elif structure == BOARDSETTING:
                    value = getattr(board, field_name, '')
                
                if value is not None:
                    if field_name == 'sweepmode':
                        widget_info['var'].set(f"{value:08x}")
                    else:
                        widget_info['var'].set(str(value))
                    
                    widget_info['status'].config(foreground="green")
            
            self.modified_settings.clear()
            self._update_status("Settings loaded", "green")
            
        except Exception as e:
            self._update_status(f"Error loading settings: {e}", "red")
            messagebox.showerror("Error", f"Failed to load settings: {e}")
    
    def update_settings_display(self, settings_dict, structure_getter):
        """Update settings display with current values"""
        try:
            structure = structure_getter()
            
            for key in settings_dict:
                value = getattr(structure, key, None)
                if value is not None:
                    if key == 'sweepmode':
                        value = f"{value:08x}"
                    settings_dict[key]['value'].set(str(value))
                    
        except Exception as e:
            self.output_callback(f"Settings Update Error: {str(e)}\n")
    
    # Helper methods
    def _mark_modified(self, field_name):
        """Mark a setting as modified"""
        self.modified_settings.add(field_name)
        widget_info = self.channel_widgets.get(field_name)
        if widget_info and 'status' in widget_info:
            widget_info['status'].config(foreground="orange")
    
    def _update_status(self, message, color="black"):
        """Update status label"""
        if hasattr(self, 'channel_status_label'):
            self.channel_status_label.config(text=message, foreground=color)
    
    def _on_channel_change(self, event=None):
        """Handle channel selection change"""
        self.current_channel = self.channel_var.get()
        self.load_channel_settings()
    
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
    
    def _open_bitfield_editor(self, field_name, var, label):
        """Open a bitfield editor dialog"""
        BitfieldEditor(self.channel_parent, field_name, var, label)