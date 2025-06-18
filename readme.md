# MCS8 Control Software

A Python-based GUI application for controlling and visualizing data from MCS8 multi-channel scaler devices.

## Overview

This software provides a user-friendly interface for the MCS8 multi-channel scaler device through the dmcs8.dll library. It offers comprehensive control over acquisition settings, data management, and real-time visualization of spectra.

## Features

- **Complete Device Control**: Start, stop, continue, and erase measurements
- **Real-time Data Visualization**: Display active channels with automatic updates
- **Configuration Management**: 
  - View and modify acquisition settings
  - Configure data storage options
  - Adjust board settings
- **File Operations**: 
  - Load and save MPA files
  - Save device configurations

## Requirements

- Windows operating system
- Python 3.6+
- Required libraries:
  - tkinter
  - numpy
  - matplotlib
  - ctypes

## Installation

1. Ensure the dmcs8.dll file is available in the same directory as the script or in your system PATH
2. Install required Python dependencies:
   ```
   pip install numpy matplotlib
   ```

## Usage

Run the application:
```
python mcs8_control.py
```

### Main Controls

- **▶**: Start measurement
- **■**: Stop measurement
- **⏵**: Continue measurement
- **⌫**: Erase data

### Tabs

- **AcqStatus**: View current acquisition status
- **AcqSettings**: Configure acquisition parameters (spectrum length, ROI, etc.)
- **DatSettings**: Configure data storage settings
- **BoardSettings**: Adjust board operational parameters
- **DataDisplay**: Visualize spectrum data with interactive plots

### File Operations

- **Browse**: Select MPA files
- **Load MPA**: Load existing data files
- **Save Config**: Save current configuration to MCS8A.SET
- **Save MPA**: Save current data and configuration

## Settings Configuration

Each settings tab provides:
- Current status display
- Configuration fields with tooltips
- Apply buttons for immediate update

## Notes

- The application automatically refreshes status information
- The spectrum display updates when the tab is selected or manually refreshed
- For advanced operations, direct commands can be sent via the API