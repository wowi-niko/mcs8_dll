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