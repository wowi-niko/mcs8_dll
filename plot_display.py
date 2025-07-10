import tkinter as tk
from tkinter import ttk
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import LogNorm
from typing import Tuple, List, Dict
import time
from mcs8_func import MCS8
# Add these imports to your existing imports
import threading
from dataclasses import dataclass
from enum import Enum
import hashlib

class MCSDisplay:
    def __init__(self, tab_display: ttk.Frame, mcs: 'MCS8'):
        self.tab_display = tab_display
        self.mcs = mcs
        self.fig = None
        self.axes = {}  # Dictionary to store axes by channel
        self.lines = {}  # Dictionary to store line objects by channel
        self.images = {}  # Dictionary to store 2D/3D image/surface objects
        self.canvas = None
        self.notebook = None
        self.colormaps = ['gist_ncar', 'hot', 'viridis', 'plasma', 'inferno', 'magma', 'jet', 'rainbow', 'coolwarm', 'twilight']
        
        # Cache for channel data to detect changes
        self.channel_cache = {}
        self.active_channels_cache = set()
        self.last_update_time = 0
        self.update_interval = 0.1  # Minimum time between updates (seconds)
        
        # Performance flags
        self.use_blitting = True  # Enable blitting for faster updates
        self.background = None

        self.fixed_ylims = {}  # Dictionary to store fixed y-limits by channel
        self.y_axis_fixed = True  # Flag to enable/disable fixed y-axis
        
        # Initial setup
        self._setup_plot_params()
        self.create_display()
        self._isplaying = False
    
    def _set_playing(self):
        self._isplaying = False
        
    def _setup_plot_params(self):
        """Set up matplotlib parameters for better performance and compact layout"""
        plt.rcParams.update({
            'font.size': 8,
            'axes.titlesize': 9,
            'axes.labelsize': 8,
            'xtick.labelsize': 7,
            'ytick.labelsize': 7,
            'legend.fontsize': 7,
            'figure.titlesize': 10,
            'figure.subplot.top': 0.95,      # Reduced top margin
            'figure.subplot.bottom': 0.12,   # Reduced bottom margin
            'figure.subplot.left': 0.12,     # Reduced left margin
            'figure.subplot.right': 0.95,    # Reduced right margin
            'figure.subplot.wspace': 0.1,    # Reduced horizontal spacing
            'figure.subplot.hspace': 0.15,   # Significantly reduced vertical spacing
            'axes.formatter.use_mathtext': True,
            'axes.formatter.limits': (-3, 3),
            'axes.grid': True,
            'grid.alpha': 0.3,
            'path.simplify': True,  # Simplify paths for performance
            'path.simplify_threshold': 1.0,
            'agg.path.chunksize': 10000  # Larger chunks for better performance
        })

    def create_display(self):
        """Create the initial display structure"""
        # Clear existing display
        self._clear_display()
        
        # Get initial channel data
        active_channels, channel_data, is2d = self._get_channel_data()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.tab_display)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create main tab
        main_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text="All Channels")
        
        # Create the figure and initial plots
        self._create_figure_and_plots(active_channels, channel_data, main_tab, is2d)
        
        # Create 2D/3D tabs if needed
        for idx, channel in enumerate(active_channels):
            if is2d[idx]:
                self._create_2d_3d_tab(channel, channel_data[channel])
        
        # Cache the current state
        self.active_channels_cache = set(active_channels)
        
        return self.fig, self.axes, self.canvas
    
    def preiodic_update(self):
        """Periodic update method to refresh the display"""
        while(self._isplaying):
            self.update_plot(force=False, rebuild=False)
            # wait 1 second before next update
            time.sleep(1)

    def _create_figure_and_plots(self, active_channels: List[int], channel_data: Dict[int, np.ndarray], 
                                parent_frame: ttk.Frame, is2d: List[bool]):
        """Create the figure and initial plots with shared x-axis and minimal spacing"""
        # Count 1D channels
        channels_1d = [(ch, idx) for idx, ch in enumerate(active_channels) if not is2d[idx]]
        
        if not channels_1d:
            return
        
        num_channels = len(channels_1d)
        
        # Define background color for plot areas only: rgba(36,255,255,100) converted to matplotlib format
        # Assuming alpha 100 is out of 255 scale (0.392) - adjust if needed
        plot_bg_color = (36/255, 255/255, 255/255, 100/255)  # Cyan with transparency
        # Alternative if alpha is out of 100: plot_bg_color = (36/255, 255/255, 255/255, 1.0)
        
        # Create figure with appropriate size
        fig_height = max(3, min(8, 2 + num_channels * 1.5))  # Dynamic height based on channel count
        fig_width = 10
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=100)
        
        # Store reference to shared x-axis
        shared_ax = None
        
        # Create subplots with shared x-axis and minimal spacing
        for plot_idx, (channel, data_idx) in enumerate(channels_1d):
            if num_channels == 1:
                ax = self.fig.add_subplot(111)
                shared_ax = ax
            else:
                if plot_idx == 0:
                    # First subplot - this will be the shared x-axis reference
                    ax = self.fig.add_subplot(num_channels, 1, plot_idx + 1)
                    shared_ax = ax
                else:
                    # Subsequent subplots share x-axis with the first
                    ax = self.fig.add_subplot(num_channels, 1, plot_idx + 1, sharex=shared_ax)
            
            # Set subplot background color (plot area only)
            ax.set_facecolor(plot_bg_color)
            
            # Store axis
            self.axes[channel] = ax
            
            # Create initial plot
            data = channel_data[channel]
            if data.ndim > 1 and data.shape[0] == 1:
                data = data[0]
            
            # Create line object with different colors for better distinction
            # Enhanced color palette with better contrast against cyan background
            colors = ['#000080', '#8B0000', '#006400', '#8B008B', '#FF4500', '#4B0082', '#B22222', '#2F4F4F']
            color = colors[plot_idx % len(colors)]
            
            line, = ax.plot([], [], color=color, linewidth=1.2, label=f'Channel {channel}')  # Slightly thicker lines
            self.lines[channel] = line
            
            # Set initial data
            x_data = np.arange(len(data))
            line.set_data(x_data, data)
            
            # Configure axis
            ax.set_xlim(0, len(data))
            
            # Set y-limits with better handling of edge cases
            data_min, data_max = np.min(data), np.max(data)

            if data_min == data_max:
                # Handle constant data
                y_margin = max(1, abs(data_min) * 0.1)
                ax.set_ylim(data_min - y_margin, data_max + y_margin)
            else:
                # Normal case with margin
                y_range = data_max - data_min
                margin = y_range * 0.05  # Reduced margin for more compact view
                ax.set_ylim(data_min - margin, data_max + 2*margin)
            
            # Enhanced grid styling for better visibility on cyan background
            ax.grid(True, which="both", ls="-", alpha=0.4, color='white', linewidth=0.5)
            
            # Labels and titles with better contrast
            ax.set_ylabel(f'Ch {channel+1}\nCounts', fontsize=8, color='black')
            
            # Style the tick labels for better readability
            ax.tick_params(axis='both', colors='black', labelsize=7)
            
            # Only show x-axis label and ticks on the bottom plot
            if plot_idx == num_channels - 1:
                ax.set_xlabel('Channel', fontsize=8, color='black')
                # Keep x-tick labels visible
            else:
                # Hide x-tick labels for upper plots to save space
                ax.tick_params(labelbottom=False)
            
            # Enhanced channel identification with better contrast
            if num_channels > 1:
                ax.text(0.95, 0.95, f'Ch {channel+1}', transform=ax.transAxes, 
                    fontsize=9, verticalalignment='top', weight='bold',
                    bbox=dict(boxstyle="round,pad=0.4", facecolor='white', alpha=0.8, edgecolor=color))
            
            # Style the spines (plot borders) for better definition
            for spine in ax.spines.values():
                spine.set_color('black')
                spine.set_linewidth(1)
            
            # Cache the data
            self.channel_cache[channel] = data.copy()
        
        # Adjust layout with minimal spacing
        if num_channels == 1:
            self.fig.tight_layout(pad=1.5)
        else:
            # Use subplots_adjust for better control over spacing
            self.fig.subplots_adjust(
                left=0.12,    # Left margin
                right=0.95,   # Right margin  
                top=0.95,     # Top margin
                bottom=0.1,   # Bottom margin
                hspace=0.2    # Minimal vertical spacing between subplots
            )
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.canvas.draw()
        
        # Create toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, parent_frame)
        toolbar.update()
        
        # Pack canvas
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        # Store background for blitting
        if self.use_blitting:
            self.background = self.canvas.copy_from_bbox(self.fig.bbox)

    def update_plot(self, force: bool = False, rebuild: bool = False):
        """Update the plot with new data
        
        Args:
            force: Force update even if within rate limit
            rebuild: Force complete rebuild of display
        """
        # Rate limiting (unless forced or rebuilding)
        current_time = time.time()
        if not force and not rebuild and (current_time - self.last_update_time) < self.update_interval:
            return
        
        self.last_update_time = current_time
        
        try:
            # Force rebuild if requested
            if rebuild:
                print("Forcing complete display rebuild...")
                self.create_display()
                return
            
            # Get current data
            active_channels, channel_data, is2d = self._get_channel_data()
            active_set = set(active_channels)
            
            # Check if channel configuration has changed
            if active_set != self.active_channels_cache:
                # Full rebuild needed
                print("Channel configuration changed, rebuilding display...")
                self.create_display()
                return
            
            # Check if data dimensions have changed for any channel
            for channel in active_channels:
                if channel in self.channel_cache:
                    old_shape = self.channel_cache[channel].shape
                    new_shape = channel_data[channel].shape
                    if old_shape != new_shape:
                        print(f"Data dimensions changed for channel {channel}, rebuilding display...")
                        self.create_display()
                        return
            
            # Update existing plots
            self._update_existing_plots(active_channels, channel_data, is2d)
            self.reset_canvas()  # Reset canvas to apply changes
            
        except Exception as e:
            print(f"Error updating plot: {e}")
            # On error, try rebuilding the display
            try:
                self.create_display()
            except Exception as rebuild_error:
                print(f"Error rebuilding display: {rebuild_error}")

    def reset_canvas(self):
        """Simuliert den Effekt des Home-Buttons: vollständige Neuzeichnung und Reset des Blitting"""
        if self.canvas:
            # Erzwinge vollständige Neuzeichnung
            self.canvas.draw()
            
            # Aktualisiere den Blitting-Hintergrund
            self.background = self.canvas.copy_from_bbox(self.fig.bbox)

    def _update_existing_plots(self, active_channels: List[int], channel_data: Dict[int, np.ndarray], 
                              is2d: List[bool]):
        """Update only the data in existing plots with improved y-axis scaling"""
        updated = False
        
        # Update 1D plots
        for idx, channel in enumerate(active_channels):
            if is2d[idx]:
                # Update 2D/3D plots
                if channel in self.images:
                    self._update_2d_3d_image(channel)
                continue
            
            data = channel_data[channel]
            if data.ndim > 1 and data.shape[0] == 1:
                data = data[0]
            
            # Check if data has changed
            if channel not in self.channel_cache or not np.array_equal(data, self.channel_cache[channel]):
                # Update line data
                if channel in self.lines:
                    line = self.lines[channel]
                    line.set_ydata(data)
                    
                    # Update axis limits with better scaling
                    ax = self.axes[channel]
                    
                    # Update x-axis if data length changed
                    if len(data) != len(self.channel_cache.get(channel, [])):
                        x_data = np.arange(len(data))
                        line.set_xdata(x_data)
                        ax.set_xlim(0, len(data))
                    
                    # Smart y-axis scaling
                    data_min, data_max = np.min(data), np.max(data)
                    
                    if data_min == data_max:
                        # Handle constant data
                        y_margin = max(1, abs(data_min) * 0.1)
                        new_ylim = (data_min - y_margin, data_max + y_margin)
                    else:
                        # Calculate range with reduced margin for compact view
                        y_range = data_max - data_min
                        margin = y_range * 0.05  # Smaller margin
                        new_ylim = (data_min - margin, data_max + margin)
                    
                    # Only update if the change is significant to avoid constant rescaling
                    current_ylim = ax.get_ylim()
                    ylim_change = abs(new_ylim[0] - current_ylim[0]) / (current_ylim[1] - current_ylim[0])
                    ylim_change += abs(new_ylim[1] - current_ylim[1]) / (current_ylim[1] - current_ylim[0])
                    
                    if ylim_change > 0.1:  # Only update if change is > 10%
                        ax.set_ylim(new_ylim)
                    
                    # Cache new data
                    self.channel_cache[channel] = data.copy()
                    updated = True
        
        if updated:
            if self.use_blitting and self.background is not None:
                # Restore background
                self.canvas.restore_region(self.background)
                
                # Redraw all lines
                for line in self.lines.values():
                    line.axes.draw_artist(line)
                
                # Blit
                self.canvas.blit(self.fig.bbox)
            else:
                # Regular draw
                self.canvas.draw_idle()

    def _create_2d_3d_tab(self, channel: int, data: np.ndarray):
        """Create a dedicated tab for 2D/3D data visualization"""
        if data.ndim <= 1:
            return
        
        # Create tab
        tab_2d_3d = ttk.Frame(self.notebook)
        self.notebook.add(tab_2d_3d, text=f"2D/3D Ch {channel}")
        
        # Create control frame
        control_frame = ttk.Frame(tab_2d_3d)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Create controls
        # Log scale toggle
        log_var = tk.BooleanVar(value=True)
        log_check = ttk.Checkbutton(
            control_frame, 
            text="Log Scale", 
            variable=log_var,
            command=lambda: self._update_2d_3d_plot_full(channel)
        )
        log_check.pack(side=tk.LEFT, padx=10)
        
        # 3D mode toggle
        mode_3d_var = tk.BooleanVar(value=False)
        mode_3d_check = ttk.Checkbutton(
            control_frame, 
            text="3D View", 
            variable=mode_3d_var,
            command=lambda: self._toggle_3d_mode(channel)
        )
        mode_3d_check.pack(side=tk.LEFT, padx=10)
        
        # Colormap selection
        cmap_var = tk.StringVar(value='gist_ncar')
        cmap_label = ttk.Label(control_frame, text="Colormap:")
        cmap_label.pack(side=tk.LEFT, padx=(20, 5))
        cmap_combo = ttk.Combobox(
            control_frame, 
            textvariable=cmap_var, 
            values=self.colormaps, 
            width=12,
            state="readonly"
        )
        cmap_combo.pack(side=tk.LEFT, padx=5)
        cmap_combo.bind("<<ComboboxSelected>>", lambda e: self._update_2d_3d_plot_full(channel))
        
        # 3D specific controls
        stride_var = tk.IntVar(value=1)
        stride_label = ttk.Label(control_frame, text="3D Stride:")
        stride_label.pack(side=tk.LEFT, padx=(20, 5))
        stride_spin = ttk.Spinbox(
            control_frame,
            from_=1,
            to=10,
            textvariable=stride_var,
            width=5,
            command=lambda: self._update_3d_stride(channel)
        )
        stride_spin.pack(side=tk.LEFT, padx=5)
        
        # Create plot frame
        plot_frame = ttk.Frame(tab_2d_3d)
        plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create figure
        fig_2d_3d = Figure(dpi=100)
        
        # Start with 2D plot
        ax_2d_3d = fig_2d_3d.add_subplot(111)
        
        # Store references
        fig_2d_3d.channel_id = channel
        
        # Create canvas
        canvas_2d_3d = FigureCanvasTkAgg(fig_2d_3d, master=plot_frame)
        
        # Initial 2D plot
        data_plot = self._prepare_2d_data(data)
        
        try:
            if log_var.get():
                im = ax_2d_3d.imshow(
                    data_plot, 
                    aspect='auto',
                    cmap=cmap_var.get(),
                    norm=LogNorm(vmin=max(data_plot.min(), 1e-10), vmax=data_plot.max()),
                    interpolation='nearest'
                )
            else:
                im = ax_2d_3d.imshow(
                    data_plot, 
                    aspect='auto',
                    cmap=cmap_var.get(),
                    interpolation='nearest'
                )
            
            ax_2d_3d.invert_yaxis()
            cbar = fig_2d_3d.colorbar(im, ax=ax_2d_3d, pad=0.02)
            cbar.set_label('Counts', fontsize=8)
        except Exception as e:
            print(f"Error creating initial 2D plot for channel {channel}: {e}")
            # Create a simple fallback plot
            im = ax_2d_3d.imshow(data_plot, aspect='auto', cmap=cmap_var.get())
            ax_2d_3d.invert_yaxis()
            cbar = fig_2d_3d.colorbar(im, ax=ax_2d_3d, pad=0.02)
            cbar.set_label('Counts', fontsize=8)
        
        # Store everything including the control variables
        self.images[channel] = {
            'im': im,
            'ax': ax_2d_3d,
            'fig': fig_2d_3d,
            'canvas': canvas_2d_3d,
            'cbar': cbar,
            'log_var': log_var,
            'cmap_var': cmap_var,
            'mode_3d_var': mode_3d_var,
            'stride_var': stride_var,
            'tab': tab_2d_3d,
            'plot_frame': plot_frame,
            'is_3d': False,
            'surface': None  # For 3D surface object
        }
        
        # Layout
        ax_2d_3d.set_xlabel('X Dimension', fontsize=8)
        ax_2d_3d.set_ylabel('Y Dimension', fontsize=8)
        fig_2d_3d.tight_layout(pad=3.0)
        
        # Add toolbar
        toolbar_2d_3d = NavigationToolbar2Tk(canvas_2d_3d, plot_frame)
        toolbar_2d_3d.update()
        
        # Pack canvas
        canvas_2d_3d.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        canvas_2d_3d.draw()

    def _toggle_3d_mode(self, channel: int):
        """Toggle between 2D and 3D view for a channel"""
        if channel not in self.images:
            return
        
        img_info = self.images[channel]
        is_3d = img_info['mode_3d_var'].get()
        
        try:
            # Clear current plot (this also removes the colorbar safely)
            img_info['fig'].clear()
            
            if is_3d:
                # Switch to 3D
                ax = img_info['fig'].add_subplot(111, projection='3d')
                img_info['is_3d'] = True
                self._create_3d_plot(channel, ax)
            else:
                # Switch to 2D
                ax = img_info['fig'].add_subplot(111)
                img_info['is_3d'] = False
                self._create_2d_plot(channel, ax)
            
            # Update stored axis
            img_info['ax'] = ax
            
            # Redraw
            img_info['fig'].tight_layout(pad=3.0)
            img_info['canvas'].draw()
            
        except Exception as e:
            print(f"Error toggling 3D mode for channel {channel}: {e}")
            # Reset the checkbox to previous state
            img_info['mode_3d_var'].set(not is_3d)
            # Try to recreate the plot in the original mode
            try:
                self._update_2d_3d_plot_full(channel)
            except Exception as e2:
                print(f"Error during fallback recreation: {e2}")

    def _create_2d_plot(self, channel: int, ax):
        """Create 2D plot for the channel"""
        if channel not in self.images:
            return
        
        img_info = self.images[channel]
        
        # Get current data
        active_channels, channel_data, _ = self._get_channel_data()
        
        if channel not in channel_data:
            return
        
        data = channel_data[channel]
        
        if data is None or data.ndim <= 1:
            return
        
        # Prepare data
        data_plot = self._prepare_2d_data(data)
        
        # Get current settings
        use_log = img_info['log_var'].get()
        cmap = img_info['cmap_var'].get()
        
        # Create 2D image
        if use_log:
            im = ax.imshow(
                data_plot, 
                aspect='auto',
                cmap=cmap,
                norm=LogNorm(vmin=max(data_plot.min(), 1e-10), vmax=data_plot.max()),
                interpolation='nearest'
            )
        else:
            im = ax.imshow(
                data_plot, 
                aspect='auto',
                cmap=cmap,
                interpolation='nearest'
            )
        
        ax.invert_yaxis()
        
        # Create new colorbar (old one was cleared with fig.clear())
        cbar = img_info['fig'].colorbar(im, ax=ax, pad=0.02)
        cbar.set_label('Counts', fontsize=8)
        
        # Update stored references
        img_info['im'] = im
        img_info['cbar'] = cbar
        img_info['surface'] = None
        
        # Labels
        ax.set_xlabel('X Dimension', fontsize=8)
        ax.set_ylabel('Y Dimension', fontsize=8)

    def _create_3d_plot(self, channel: int, ax):
        """Create 3D surface plot for the channel"""
        if channel not in self.images:
            return
        
        img_info = self.images[channel]
        
        # Get current data
        active_channels, channel_data, _ = self._get_channel_data()
        
        if channel not in channel_data:
            return
        
        data = channel_data[channel]
        
        if data is None or data.ndim <= 1:
            return
        
        # Prepare data
        data_plot = self._prepare_2d_data(data)
        
        # Get current settings
        use_log = img_info['log_var'].get()
        cmap = img_info['cmap_var'].get()
        stride = img_info['stride_var'].get()
        
        # Apply log scale if needed
        if use_log:
            z_data = np.log10(data_plot + 1e-10)
        else:
            z_data = data_plot
        
        # Create meshgrid
        y_size, x_size = data_plot.shape
        x = np.arange(0, x_size, stride)
        y = np.arange(0, y_size, stride)
        X, Y = np.meshgrid(x, y)
        
        # Downsample Z data according to stride
        Z = z_data[::stride, ::stride]
        
        # Create 3D surface
        surface = ax.plot_surface(
            X, Y, Z,
            cmap=cmap,
            alpha=0.9,
            linewidth=0,
            antialiased=True,
            rcount=min(50, Z.shape[0]),  # Limit resolution for performance
            ccount=min(50, Z.shape[1])
        )
        
        # Create new colorbar (old one was cleared with fig.clear())
        cbar = img_info['fig'].colorbar(surface, ax=ax, pad=0.1, shrink=0.8)
        cbar.set_label('Counts (log scale)' if use_log else 'Counts', fontsize=8)
        
        # Update stored references
        img_info['surface'] = surface
        img_info['cbar'] = cbar
        img_info['im'] = None
        
        # Labels and view
        ax.set_xlabel('X Dimension', fontsize=8)
        ax.set_ylabel('Y Dimension', fontsize=8)
        ax.set_zlabel('Counts (log scale)' if use_log else 'Counts', fontsize=8)
        
        # Set a nice viewing angle
        ax.view_init(elev=30, azim=45)

    def _update_3d_stride(self, channel: int):
        """Update 3D plot when stride changes"""
        if channel not in self.images:
            return
        
        img_info = self.images[channel]
        if img_info['is_3d']:
            self._update_2d_3d_plot_full(channel)

    def _prepare_2d_data(self, data: np.ndarray) -> np.ndarray:
        """Prepare 2D data for plotting"""
        data_plot = data.copy()
        
        # Ensure non-negative values
        min_val = np.min(data_plot)
        if min_val < 0:
            data_plot = data_plot - min_val
        
        # Add small epsilon for log scale
        data_plot = data_plot + 1e-10
        
        return data_plot

    def _update_2d_3d_plot_full(self, channel: int):
        """Completely redraw 2D/3D plot with new settings (for UI controls)"""
        if channel not in self.images:
            return
        
        img_info = self.images[channel]
        
        try:
            # Clear the current plot (this also removes the colorbar safely)
            img_info['fig'].clear()
            
            if img_info['is_3d']:
                # Recreate 3D plot
                ax = img_info['fig'].add_subplot(111, projection='3d')
                self._create_3d_plot(channel, ax)
            else:
                # Recreate 2D plot
                ax = img_info['fig'].add_subplot(111)
                self._create_2d_plot(channel, ax)
            
            # Update stored axis
            img_info['ax'] = ax
            
            # Update layout and redraw
            img_info['fig'].tight_layout(pad=3.0)
            img_info['canvas'].draw()
            
        except Exception as e:
            print(f"Error updating 2D/3D plot for channel {channel}: {e}")
            # Try a basic fallback
            try:
                img_info['fig'].clear()
                ax = img_info['fig'].add_subplot(111)
                ax.text(0.5, 0.5, f'Error displaying Channel {channel}', 
                       ha='center', va='center', transform=ax.transAxes)
                img_info['ax'] = ax
                img_info['canvas'].draw()
            except Exception as e2:
                print(f"Error during fallback display: {e2}")

    def _update_2d_3d_image(self, channel: int):
        """Update 2D/3D image data efficiently (for automatic updates)"""
        if channel not in self.images:
            return
        
        img_info = self.images[channel]
        
        # Get current data
        active_channels, channel_data, _ = self._get_channel_data()
        
        if channel not in channel_data:
            return
        
        data = channel_data[channel]
        
        if data is None or data.ndim <= 1:
            return
        
        # For efficiency, only update if not in 3D mode during automatic updates
        # 3D updates are more expensive and should be done manually
        if img_info['is_3d']:
            return  # Skip automatic updates for 3D
        
        # Prepare data
        data_plot = self._prepare_2d_data(data)
        
        # Update 2D image data
        if img_info['im'] is not None:
            try:
                img_info['im'].set_data(data_plot)
                
                # Update normalization based on current settings
                use_log = img_info['log_var'].get()
                
                if use_log:
                    img_info['im'].set_norm(LogNorm(vmin=max(data_plot.min(), 1e-10), vmax=data_plot.max()))
                else:
                    img_info['im'].set_norm(None)
                    img_info['im'].set_clim(vmin=data_plot.min(), vmax=data_plot.max())
                
                # Redraw
                img_info['canvas'].draw_idle()
            except Exception as e:
                print(f"Error updating 2D image for channel {channel}: {e}")
                # If update fails, do a full rebuild
                self._update_2d_3d_plot_full(channel)

    def _clear_display(self):
        """Clear the display"""
        # Clear references
        self.lines.clear()
        self.axes.clear()
        self.images.clear()
        self.channel_cache.clear()
        
        # Destroy widgets
        for widget in self.tab_display.winfo_children():
            widget.destroy()
    


    def force_rebuild(self):
        """Force a complete rebuild of the display
        
        This should be called when loading new data files or when
        the data format might have changed completely.
        """
        print("Forcing complete display rebuild...")
        
        # Clear all caches
        self.channel_cache.clear()
        self.active_channels_cache.clear()
        self.lines.clear()
        self.axes.clear()
        self.images.clear()
        self.background = None
        
        # Rebuild from scratch
        self.create_display()

    def _get_channel_data(self) -> Tuple[List[int], Dict[int, np.ndarray], List[bool]]:
        """Get channel data from MCS8 with robust handling for 8 channels"""
        active_channels = []
        channel_data = {}
        is2d = []
        
        try:

            # Check all 8 channels (0-7) for MCS8
            for channel in range(16):
                try:
                    # Get acquisition settings
                    acq = self.mcs.get_acq_setting(channel)
                    range_val = acq.range
                    xdim = getattr(acq, 'xdim', 0)

                    # Get data for this channel
                    data = self.mcs.get_block(0, range_val, channel_id=channel)
                    
                    # Convert to numpy array for consistency
                    data_array = np.array(data)
                    
                    # Check if channel has meaningful data
                    if np.any(data_array != 0):
                        
                        # Check if this might be 2D data
                        # For MCS8, this would need to be determined based on your specific setup
                        # For now, assume 1D data unless we can detect 2D structure

                        if xdim > 0:
                            ydim = int(range_val / xdim)
                            data_array = data_array.reshape((ydim, -1))
                            is_2d_channel = True
                        
                        else:
                            is_2d_channel = False

                        channel_data[channel] = data_array
                        active_channels.append(channel)
                        is2d.append(is_2d_channel)
                        
                except Exception as e:
                    print(f"Error reading data from channel {channel}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error getting channel data: {e}")
            # Return empty data if there's a problem
            return [], {}, []
        
        return active_channels, channel_data, is2d
    


class ChangeType(Enum):
    NO_CHANGE = 0
    DATA_CHANGE = 1
    SCALE_CHANGE = 2
    DIMENSION_CHANGE = 3

@dataclass
class ChannelState:
    """Track state of each channel for efficient change detection"""
    data_hash: str = ""
    shape: tuple = ()
    data_range: tuple = (0, 0)
    statistical_signature: tuple = (0, 0, 0, 0)  # min, max, mean, std
    last_update: float = 0
    x_limits: tuple = (0, 1)
    y_limits: tuple = (0, 1)
    update_count: int = 0

class EfficientUpdateMixin:
    """Mixin class to add efficient update capabilities to MCSDisplay"""
    
    def __init_efficient_updates__(self):
        """Initialize the efficient update system"""
        # State tracking
        self.channel_states = {}  # Channel ID -> ChannelState
        self.update_thread = None
        self.update_stop_event = threading.Event()
        self.update_running = False
        
        # Configuration
        self.adaptive_update_interval = 0.1  # Base update interval
        self.max_update_interval = 2.0  # Maximum interval when no changes
        self.min_update_interval = 0.3  # Minimum interval during rapid changes
        self.change_threshold = 0.01  # Relative change threshold for rescaling
        self.stability_frames = 5  # Frames to wait before considering data stable
        
        # Performance tracking
        self.update_performance = {
            'total_updates': 0,
            'data_updates': 0,
            'scale_updates': 0,
            'skipped_updates': 0,
            'avg_update_time': 0
        }
        
        # Axis scaling parameters
        self.axis_scaling = {
            'y_margin_factor': 0.05,  # 5% margin on y-axis
            'y_stability_threshold': 0.01,  # 1% change needed to rescale
            'x_auto_extend': True,  # Automatically extend x-axis for new data
            'adaptive_margins': True,  # Use adaptive margins based on data variability
        }

    def start_efficient_updates(self):
        """Start the efficient update system in a separate thread"""
        if self.update_running:
            return
            
        # Initialize the system
        if not hasattr(self, 'channel_states'):
            self.__init_efficient_updates__()
            
        self.update_stop_event.clear()
        self.update_running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def stop_efficient_updates(self):
        """Stop the efficient update system"""
        if not self.update_running:
            return
            
        self.update_stop_event.set()
        self.update_running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)

    def _update_loop(self):
        """Main update loop running in separate thread"""
        current_interval = self.adaptive_update_interval
        no_change_count = 0
        
        while not self.update_stop_event.wait(current_interval):
            start_time = time.time()
            
            try:
                # Check for changes and update accordingly
                changes_detected = self._check_and_update_channels()
                
                # Adaptive interval adjustment
                if changes_detected:
                    no_change_count = 0
                    current_interval = max(self.min_update_interval, current_interval * 0.9)
                else:
                    no_change_count += 1
                    if no_change_count > self.stability_frames:
                        current_interval = min(self.max_update_interval, current_interval * 1.1)
                
                # Update performance stats
                update_time = time.time() - start_time
                self._update_performance_stats(update_time, changes_detected)
                
            except Exception as e:
                print(f"Error in update loop: {e}")
                # On error, fall back to slower updates
                current_interval = self.adaptive_update_interval

    def _check_and_update_channels(self) -> bool:
        """Check all channels for changes and update as needed"""
        try:
            # Get current data
            active_channels, channel_data, is2d = self._get_channel_data()
            
            changes_detected = False
            channels_to_update = []
            
            # Check each active channel for changes
            for idx, channel in enumerate(active_channels):
                if is2d[idx]:
                    # Handle 2D/3D data separately
                    change_type = self._detect_2d_changes(channel, channel_data[channel])
                else:
                    # Handle 1D data
                    change_type = self._detect_1d_changes(channel, channel_data[channel])
                
                if change_type != ChangeType.NO_CHANGE:
                    channels_to_update.append((channel, change_type, is2d[idx]))
                    changes_detected = True
            
            # Update channels that have changed
            if channels_to_update:
                self._update_changed_channels(channels_to_update, channel_data)
            
            # Check for new/removed channels
            current_set = set(active_channels)
            cached_set = set(self.channel_states.keys())
            if current_set != cached_set:
                print("Channel configuration changed - triggering rebuild")
                # Schedule a rebuild on the main thread
                if hasattr(self, 'tab_display'):
                    self.tab_display.after_idle(self.force_rebuild)
                return True
            
            return changes_detected
            
        except Exception as e:
            print(f"Error checking channel changes: {e}")
            return False

    def _detect_1d_changes(self, channel: int, data: np.ndarray) -> ChangeType:
        """Detect changes in 1D channel data"""
        if data.ndim > 1 and data.shape[0] == 1:
            data = data[0]
        
        # Get or create channel state
        if channel not in self.channel_states:
            self.channel_states[channel] = ChannelState()
        
        state = self.channel_states[channel]
        current_time = time.time()
        
        # Quick hash check for data changes
        data_bytes = data.tobytes()
        current_hash = hashlib.md5(data_bytes).hexdigest()
        
        if current_hash == state.data_hash:
            return ChangeType.NO_CHANGE
        
        # Data has changed - analyze the type of change
        current_shape = data.shape
        current_range = (np.min(data), np.max(data))
        current_stats = (
            current_range[0], 
            current_range[1], 
            np.mean(data), 
            np.std(data)
        )
        
        change_type = ChangeType.DATA_CHANGE
        
        # Check for dimension changes
        if current_shape != state.shape:
            change_type = ChangeType.DIMENSION_CHANGE
        # Check for significant scale changes
        elif self._significant_scale_change(state.statistical_signature, current_stats):
            change_type = ChangeType.SCALE_CHANGE
        
        # Update state
        state.data_hash = current_hash
        state.shape = current_shape
        state.data_range = current_range
        state.statistical_signature = current_stats
        state.last_update = current_time
        state.update_count += 1
        
        return change_type

    def _detect_2d_changes(self, channel: int, data: np.ndarray) -> ChangeType:
        """Detect changes in 2D/3D channel data"""
        if data.ndim <= 1:
            return ChangeType.NO_CHANGE
        
        # Get or create channel state
        if channel not in self.channel_states:
            self.channel_states[channel] = ChannelState()
        
        state = self.channel_states[channel]
        
        # For 2D data, use shape and statistical signature for change detection
        current_shape = data.shape
        current_stats = (
            np.min(data), 
            np.max(data), 
            np.mean(data), 
            np.std(data)
        )
        
        # Check for changes
        if (current_shape == state.shape and 
            np.allclose(current_stats, state.statistical_signature, rtol=self.change_threshold)):
            return ChangeType.NO_CHANGE
        
        change_type = ChangeType.DATA_CHANGE
        if current_shape != state.shape:
            change_type = ChangeType.DIMENSION_CHANGE
        elif self._significant_scale_change(state.statistical_signature, current_stats):
            change_type = ChangeType.SCALE_CHANGE
        
        # Update state
        state.shape = current_shape
        state.statistical_signature = current_stats
        state.last_update = time.time()
        state.update_count += 1
        
        return change_type

    def _significant_scale_change(self, old_stats: tuple, new_stats: tuple) -> bool:
        """Determine if the scale change is significant enough to warrant axis rescaling"""
        if not old_stats or len(old_stats) < 4 or len(new_stats) < 4:
            return True
        
        old_min, old_max, old_mean, old_std = old_stats
        new_min, new_max, new_mean, new_std = new_stats
        
        # Calculate relative changes
        if old_max != old_min:
            range_change = abs((new_max - new_min) - (old_max - old_min)) / (old_max - old_min)
        else:
            range_change = 1.0 if new_max != new_min else 0.0
        
        if old_mean != 0:
            mean_change = abs(new_mean - old_mean) / abs(old_mean)
        else:
            mean_change = 1.0 if new_mean != 0 else 0.0
        
        # Significant if range changed by more than threshold or mean shifted significantly
        return (range_change > self.axis_scaling['y_stability_threshold'] or 
                mean_change > self.axis_scaling['y_stability_threshold'])

    def _update_changed_channels(self, channels_to_update: list, channel_data: dict):
        """Update only the channels that have changed"""
        def update_on_main_thread():
            try:
                for channel, change_type, is_2d in channels_to_update:
                    if is_2d:
                        self._update_2d_channel_efficient(channel, change_type)
                    else:
                        self._update_1d_channel_efficient(channel, change_type, channel_data[channel])
                        
                # Update canvas once for all changes
                if self.canvas:
                    self.canvas.draw_idle()
                    
            except Exception as e:
                print(f"Error updating changed channels: {e}")
        
        # Schedule update on main thread
        if hasattr(self, 'tab_display'):
            self.tab_display.after_idle(update_on_main_thread)

    def _update_1d_channel_efficient(self, channel: int, change_type: ChangeType, data: np.ndarray):
        """Efficiently update a 1D channel based on change type"""
        if channel not in self.lines or channel not in self.axes:
            return
        
        if data.ndim > 1 and data.shape[0] == 1:
            data = data[0]
        
        line = self.lines[channel]
        ax = self.axes[channel]
        state = self.channel_states[channel]
        
        # Update line data
        x_data = np.arange(len(data))
        line.set_data(x_data, data)
        
        # Handle axis scaling based on change type
        if change_type in [ChangeType.DIMENSION_CHANGE, ChangeType.SCALE_CHANGE]:
            # Update x-axis if data length changed
            if len(data) != len(self.channel_cache.get(channel, [])):
                ax.set_xlim(0, len(data))
                state.x_limits = (0, len(data))
            
            # Smart y-axis scaling
            new_y_limits = self._calculate_optimal_y_limits(data, state)
            if new_y_limits != state.y_limits:
                ax.set_ylim(new_y_limits)
                state.y_limits = new_y_limits
        
        # Update cache
        self.channel_cache[channel] = data.copy()

    def _update_2d_channel_efficient(self, channel: int, change_type: ChangeType):
        """Efficiently update a 2D/3D channel"""
        if channel in self.images:
            # For 2D/3D, delegate to existing update method
            # but only for significant changes
            if change_type != ChangeType.DATA_CHANGE:
                self._update_2d_3d_image(channel)

    def _calculate_optimal_y_limits(self, data: np.ndarray, state: ChannelState) -> tuple:
        """Calculate optimal y-axis limits with adaptive margins and stability"""
        data_min, data_max = np.min(data), np.max(data)
        
        if data_min == data_max:
            # Handle constant data
            center = data_min
            margin = max(1, abs(center) * 0.1)
            return (center - margin, center + margin)
        
        # Calculate range and margin
        data_range = data_max - data_min
        
        if self.axis_scaling['adaptive_margins']:
            # Adaptive margin based on data variability
            data_std = np.std(data)
            if data_std > 0:
                # Use larger margins for more variable data
                margin_factor = self.axis_scaling['y_margin_factor'] * (1 + data_std / data_range)
            else:
                margin_factor = self.axis_scaling['y_margin_factor']
        else:
            margin_factor = self.axis_scaling['y_margin_factor']
        
        margin = data_range * margin_factor
        
        # Consider previous limits for stability
        if (state.y_limits and state.update_count > self.stability_frames and 
            not self._needs_axis_expansion(data_min, data_max, state.y_limits)):
            # Keep current limits if data still fits comfortably
            return state.y_limits
        
        return (data_min - margin, data_max + margin)

    def _needs_axis_expansion(self, data_min: float, data_max: float, current_limits: tuple) -> bool:
        """Check if axis limits need to be expanded"""
        current_min, current_max = current_limits
        current_range = current_max - current_min
        
        # Expand if data approaches boundaries (within 10% of range)
        buffer = current_range * 0.1
        
        needs_expansion = (
            data_min < (current_min + buffer) or 
            data_max > (current_max - buffer)
        )
        
        return needs_expansion

    def _update_performance_stats(self, update_time: float, changes_detected: bool):
        """Update performance statistics"""
        stats = self.update_performance
        stats['total_updates'] += 1
        
        if changes_detected:
            stats['data_updates'] += 1
        else:
            stats['skipped_updates'] += 1
        
        # Running average of update time
        alpha = 0.1  # Smoothing factor
        if stats['avg_update_time'] == 0:
            stats['avg_update_time'] = update_time
        else:
            stats['avg_update_time'] = (alpha * update_time + 
                                      (1 - alpha) * stats['avg_update_time'])

    def get_update_performance(self) -> dict:
        """Get current performance statistics"""
        return self.update_performance.copy()

    def configure_efficient_updates(self, **kwargs):
        """Configure the efficient update system"""
        for key, value in kwargs.items():
            if key in ['adaptive_update_interval', 'max_update_interval', 
                      'min_update_interval', 'change_threshold', 'stability_frames']:
                setattr(self, key, value)
            elif key in self.axis_scaling:
                self.axis_scaling[key] = value
            else:
                print(f"Unknown configuration parameter: {key}")

# Extension to your existing MCSDisplay class
def extend_mcs_display():
    """Function to add efficient update capabilities to MCSDisplay"""
    
    # Create a new class that inherits from both MCSDisplay and EfficientUpdateMixin
    class EfficientMCSDisplay(MCSDisplay, EfficientUpdateMixin):
        def __init__(self, tab_display: ttk.Frame, mcs: 'MCS8'):
            # Initialize the base class
            MCSDisplay.__init__(self, tab_display, mcs)
            
            # Initialize efficient updates
            self.__init_efficient_updates__()
            
            # Override the periodic update method
            self.original_periodic_update = self.preiodic_update  # Fix typo from original
            
        def start_live_updates(self):
            """Start live updates using the efficient system"""
            self.start_efficient_updates()
            
        def stop_live_updates(self):
            """Stop live updates"""
            self.stop_efficient_updates()
            
        def preiodic_update(self):
            """Override original periodic update to use efficient system"""
            # The efficient system handles this automatically
            pass
            
        def force_rebuild(self):
            """Enhanced force rebuild that resets efficient update state"""
            # Stop updates during rebuild
            was_running = self.update_running
            if was_running:
                self.stop_efficient_updates()
                
            # Clear efficient update state
            if hasattr(self, 'channel_states'):
                self.channel_states.clear()
            
            # Call original rebuild
            MCSDisplay.force_rebuild(self)
            
            # Restart updates if they were running
            if was_running:
                self.start_efficient_updates()
    
    return EfficientMCSDisplay