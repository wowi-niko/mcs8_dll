from ctypes import Structure, c_char, c_double, c_int, c_uint
from dataclasses import dataclass, field

# --- Constants (from C# implementation) ---
class Constants:
    ST_RUNTIME = 0
    ST_OFLS = 1
    ST_TOTALSUM = 2
    ST_ROISUM = 3
    ST_ROIRATE = 4
    ST_SWEEPS = 5
    ST_STARTS = 6
    ST_ZEROEVTS = 7

# --- Structure definitions ---
class ACQSETTING(Structure):
    """Acquisition settings structure - MCS Channel Status"""
    _fields_ = [
        ("range", c_int),           # spectrum length
        ("cftfak", c_int),          # LOWORD: 256 * cft factor (t_after_peak / t_to_peak)
                                    # HIWORD: max pulse width for CFT
        ("roimin", c_int),          # lower ROI limit
        ("roimax", c_int),          # upper limit: roimin <= channel < roimax
        ("nregions", c_int),        # number of regions
        ("caluse", c_int),          # bit0: 1 if calibration used, higher bits: formula
        ("calpoints", c_int),       # number of calibration points
        ("param", c_int),           # (reserved:) for MAP and POS: LOWORD=x, HIWORD=y
        ("offset", c_int),          # (reserved:) zoomed MAPS: LOWORD: xoffset, HIWORD, yoffset
        ("xdim", c_int),            # (reserved:) x resolution of maps
        # ("type", c_int),          # ← REMOVE THIS LINE - doesn't exist in C structure
        ("bitshift", c_uint),       # LOWORD: Binwidth = 2 ^ (bitshift) - changed to c_uint
                                    # HIWORD: Threshold for Coinc
        ("active", c_int),          # Spectrum definition words for CHN1..8:
                                    # active & 0xF  ==0 not used
                                    # ... rest of comments ...
        ("eventpreset", c_double),  # ROI preset value
        ("dummy1", c_double),       # (for future use..)
        ("dummy2", c_double),       # 
        ("dummy3", c_double)        # Reserved
    ]
    
    # Add settings metadata
    settings_meta = {
        'range': {
            'label': 'Spectrum Length',
            'default': 4096,
            'tooltip': 'Spectrum length (range=)',
            'type': 'int',
            'min': 1,
            'max': 65536
        },
        'cftfak': {
            'label': 'CFT Factor',
            'default': 2580100,
            'tooltip': 'LOWORD: 256 * cft factor (t_after_peak / t_to_peak), HIWORD: max pulse width for CFT',
            'type': 'int'
        },
        'roimin': {
            'label': 'ROI Min',
            'default': 0,
            'tooltip': 'Lower ROI limit',
            'type': 'int',
            'min': 0
        },
        'roimax': {
            'label': 'ROI Max',
            'default': 4096,
            'tooltip': 'Upper ROI limit (roimin <= channel < roimax)',
            'type': 'int',
            'min': 1
        },
        'nregions': {
            'label': 'Number of Regions',
            'default': 1,
            'tooltip': 'Number of regions',
            'type': 'int',
            'min': 1
        },
        'caluse': {
            'label': 'Calibration Use',
            'default': 0,
            'tooltip': 'bit0: 1 if calibration used, higher bits: formula',
            'type': 'int'
        },
        'calpoints': {
            'label': 'Calibration Points',
            'default': 0,
            'tooltip': 'Number of calibration points',
            'type': 'int',
            'min': 0
        },
        'bitshift': {
            'label': 'Bit Shift',
            'default': 0,
            'tooltip': 'LOWORD: Binwidth = 2 ^ (bitshift), HIWORD: Threshold for Coinc',
            'type': 'int',
            'min': 0,
            'max': 15
        },
        'active': {
            'label': 'Active Mode',
            'default': 1,
            'tooltip': 'Spectrum definition (0=not used, 1=single, 3=MAP, 5=SUM, 6=DIFF, etc.)',
            'type': 'int'
        },
        'eventpreset': {
            'label': 'Event Preset',
            'default': 10.0,
            'tooltip': 'ROI preset value',
            'type': 'double',
            'min': 0.0
        }
    }

@dataclass
class DATSETTING(Structure):
    """Data settings structure"""
    
    _fields_ = [
        ("savedata", c_int),        # bit 0: auto save after stop
                                    # bit 1: write listfile
                                    # bit 2: listfile only, no evaluation
                                    # bit 5: drop zero events
        ("autoinc", c_int),         # 1 if auto increment filename
        ("fmt", c_int),             # format type (separate spectra): 
                                    # 0 == ASCII, 1 == binary,
                                    # 2 == GANAAS, 3 == EMSA, 4 == CSV
        ("mpafmt", c_int),          # format used in mpa datafiles
        ("sephead", c_int),         # separate Header
        ("smpts", c_int),           # Missing field from C# version
        ("caluse", c_int),          # Calibration use
        ("filename", c_char * 256), # Filename
        ("specfile", c_char * 256), # Spectrum file
        ("command", c_char * 256)   # Command
    ]
    
    settings_meta = {
        'savedata': {
            'label': 'Save Data Mode',
            'default': 0,
            'tooltip': 'bit0: auto save after stop, bit1: write listfile, bit2: listfile only, bit5: drop zero events',
            'type': 'int',
            'options': {
                0: 'No Save at Halt',
                1: 'Save at Halt', 
                2: 'Write list file',
                3: 'Write list & Save'
            }
        },
        'autoinc': {
            'label': 'Auto Increment',
            'default': 0,
            'tooltip': 'Enable auto increment of filename',
            'type': 'bool'
        },
        'fmt': {
            'label': 'Format Type',
            'default': 0,
            'tooltip': 'Format type for separate spectra',
            'type': 'int',
            'options': {
                0: 'ASCII',
                1: 'Binary',
                2: 'GANAAS',
                3: 'EMSA',
                4: 'CSV'
            }
        },
        'mpafmt': {
            'label': 'MPA Format',
            'default': 0,
            'tooltip': 'Format used in MPA datafiles',
            'type': 'int'
        },
        'sephead': {
            'label': 'Separate Header',
            'default': 0,
            'tooltip': 'Separate header file (.MP) and data file',
            'type': 'bool'
        },
        'filename': {
            'label': 'Filename',
            'default': '',
            'tooltip': 'Output filename',
            'type': 'string',
            'max_length': 255
        }
    }

@dataclass
class BOARDSETTING(Structure):
    """Board settings structure"""
    
    _fields_ = [
        ("sweepmode", c_int),       # sweepmode & 0xF: 0 = normal, 
                                    # 1=differential (relative to first stop in sweep)
                                    # 4=sequential
                                    # 5=seq.+diff (Ch1), bit0 = differential mode
                                    # 6 = CORRELATIONS
                                    # 7 = diff.+Corr.
                                    # 9=differential to stop in Ch2, bit3 = Ch2 ref (diff.mode)
                                    # 0xF = Corr.+diff (Ch2)
                                    # bit 4: Softw. Start
                                    # bit 5: "Don't show" tagbits
                                    # bit 6: Endless
                                    # bit 7: Start event generation
                                    # bit 8: Enable Tag bits
                                    # bit 9: start with rising edge 
                                    # bit 10: time under threshold for pulse width
                                    # bit 11: pulse width mode for any spectra with both edges enabled
                                    # bit 12: abandon Sweepcounter in Data
                                    # bit 13: "one-hot" mode with tagbits
                                    # bit 14: ch6 ref (diff.mode)
                                    # bit 16..bit 22 ~(input channel enable) 
                                    # bit 24: require data lost bit in data
                                    # bit 25: don't allow 6 byte datalength
                                    # bit 27: Folded
                                    # bit 28: Interleaved
        ("prena", c_int),           # bit 0: realtime preset enabled
                                    # bit 1: 
                                    # bit 2: sweep preset enabled
                                    # bit 3: ROI preset enabled
                                    # bit 4: Starts preset enabled
                                    # bit 5: ROI2 preset enabled
                                    # bit 6: ROI3 preset enabled
                                    # bit 7: ROI4 preset enabled
                                    # bit 8: ROI5 preset enabled
                                    # bit 9: ROI6 preset enabled
                                    # bit 10: ROI7 preset enabled
                                    # bit 11: ROI8 preset enabled
        ("cycles", c_int),          # for sequential mode
        ("sequences", c_int),       # for sequential mode
        ("syncout", c_int),         # LOWORD: sync out; bit 0..5 NIM syncout, bit 8..13 TTL syncout
                                    # bit7: NIM syncout_invert, bit15: TTL syncout_invert
                                    # 0="0", 1=5 MHz, 2=50 MHz, 3=100 MHz, 4=97.656 MHz,
                                    # 5=195.625 MHz, 6= 195 MHz (int ref), 7=Start, 8=Ch1, 9=Ch2, 10=Ch3,
                                    # 11=Ch4, 12=Ch5, 13=Ch6, 14=Ch7, 15=GO, 16=Start_of_sweep, 17=Armed,
                                    # 18=SWEEP_ON, 19=WINDOW, 20=HOLD_OFF, 21=EOS_DEADTIME
                                    # 22=TIME[0],...,51=TIME[29], 52...63=SWEEP[0]..SWEEP[11]
        ("digio", c_int),           # LOWORD: Use of Dig I/O, GO Line:
                                    # bit 0: status dig 0..3
                                    # bit 1: Output digval and increment digval after stop
                                    # bit 2: Invert polarity
                                    # bit 3: Push-Pull output, not possible
                                    # bit 4:  Start with Input Dig 4 
                                    # bit 5:  Start with Input GO 
                                    # bit 8: GOWATCH
                                    # bit 9: GO High at Start
                                    # bit 10: GO Low at Stop
                                    # bit 11: Clear at triggered start
                                    # bit 12: Only triggered start
        ("digval", c_int),          # digval=0..255 value for samplechanger
        ("dac0", c_int),            # DAC0 value (START) 
                                    # bit 16: Start with rising edge
        ("dac1", c_int),            # DAC1 value (STOP 1)
        ("dac2", c_int),            # DAC2 value (STOP 2)
        ("dac3", c_int),            # DAC3 value (STOP 3)
        ("dac4", c_int),            # DAC4 value (STOP 4)
        ("dac5", c_int),            # DAC5 value (STOP 5)
        ("dac6", c_int),            # DAC6 value (STOP 6)
        ("dac7", c_int),            # DAC7 value (STOP 7)

                                    # bit (14,15) of each word: 0=falling, 1=rising, 2=both, 3=both+CFT 
                                    # bit 17 of each: pulse width mode under threshold
        ("fdac", c_int),            # dummy
        ("tagbits", c_int),         # number of tagbits
        ("extclk", c_int),          # use external clock
        ("periods", c_int),         # number of periods in folded mode, sweeplength = range * periods
        ("serno", c_int),           # serial number
        ("ddruse", c_int),          # bit0: DDR_USE, bit1: DDR_2GB
                                    # bits[2:3]: usb_usage
                                    # bits[4:5]: wdlen
        ("active", c_int),          # module in system
        ("holdafter", c_double),    # Hold off
        ("swpreset", c_double),     # sweep preset value
        ("fstchan", c_double),      # acquisition delay
        ("timepreset", c_double)    # time preset
    ]
    
    settings_meta = {
        'sweepmode': {
            'label': 'Sweep Mode',
            'default': 0x227ea080,  # Converted from hex string to int
            'tooltip': 'Hex value controlling measurement mode and features',
            'type': 'hex',
            'options': {
                0: 'Normal',
                1: 'Differential',
                4: 'Sequential',
                5: 'Sequential + Differential',
                6: 'Correlations',
                7: 'Differential + Correlations'
            }
        },
        'prena': {
            'label': 'Preset Enable',
            'default': 4,
            'tooltip': 'Bit flags for enabling different presets (bit0: realtime, bit2: sweep, bit3: ROI, etc.)',
            'type': 'int'
        },
        'cycles': {
            'label': 'Cycles',
            'default': 18,
            'tooltip': 'Number of cycles for sequential mode',
            'type': 'int',
            'min': 1
        },
        'sequences': {
            'label': 'Sequences',
            'default': 1,
            'tooltip': 'Number of sequence repetitions',
            'type': 'int',
            'min': 1
        },
        'holdafter': {
            'label': 'Hold After',
            'default': 0.0,
            'tooltip': 'Hold after sweep in units of 64 basic dwelltimes',
            'type': 'double',
            'min': 0.0
        },
        'swpreset': {
            'label': 'Sweep Preset',
            'default': 1000000.0,
            'tooltip': 'Sweep-Preset value',
            'type': 'double',
            'min': 0.0
        },
        'timepreset': {
            'label': 'Time Preset',
            'default': 0.0,
            'tooltip': 'Time preset value',
            'type': 'double',
            'min': 0.0
        },
        'fstchan': {
            'label': 'First Channel',
            'default': 0.0,
            'tooltip': 'Acquisition delay',
            'type': 'double',
            'min': 0.0
        }
    }

class LVCOINCDEF(Structure):
    """Level coincidence definition structure"""
    
    _fields_ = [
        ("adcnum", c_int),     # Number of active ADC's
        ("tofnum", c_int),     # Number of active MCS/Scope channels
        ("ntofs0", c_int),     # Number of TOF inputs
        ("modules", c_int),    # Number of MCS8 modules
        ("nadcs", c_int)       # Number of ADCs
    ]

class ACQSTATUS(Structure):
    """Acquisition status structure"""
    
    _fields_ = [
        ("started", c_int),        # acquisition status: 1 if running, 0 else
        ("maxval", c_int),         # Maximum value
        ("cnt", c_double * 8)      # see ST_.. defines above (runtime, ofls, totalsum, roisum, roirate, sweeps, starts, zeroevts)
    ]

# Helper functions for working with structures
def get_structure_defaults(structure_class):
    """Get default values for a structure based on its metadata"""
    defaults = {}
    if hasattr(structure_class, 'settings_meta'):
        for field_name, meta in structure_class.settings_meta.items():
            defaults[field_name] = meta.get('default', 0)
    return defaults

def validate_field_value(structure_class, field_name, value):
    """Validate a field value against its metadata constraints"""
    if not hasattr(structure_class, 'settings_meta'):
        return True, "No metadata available"
    
    meta = structure_class.settings_meta.get(field_name)
    if not meta:
        return True, "No validation rules"
    
    # Type validation
    field_type = meta.get('type', 'int')
    if field_type == 'int' and not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError):
            return False, f"Value must be an integer"
    
    # Range validation
    if 'min' in meta and value < meta['min']:
        return False, f"Value must be >= {meta['min']}"
    if 'max' in meta and value > meta['max']:
        return False, f"Value must be <= {meta['max']}"
    
    # String length validation
    if field_type == 'string' and 'max_length' in meta:
        if len(str(value)) > meta['max_length']:
            return False, f"String length must be <= {meta['max_length']}"
    
    return True, "Valid"

def create_structure_instance(structure_class, **kwargs):
    """Create a structure instance with default values and optional overrides"""
    instance = structure_class()
    defaults = get_structure_defaults(structure_class)
    
    # Set defaults
    for field_name, default_value in defaults.items():
        if hasattr(instance, field_name):
            setattr(instance, field_name, default_value)
    
    # Apply overrides
    for field_name, value in kwargs.items():
        if hasattr(instance, field_name):
            is_valid, message = validate_field_value(structure_class, field_name, value)
            if is_valid:
                setattr(instance, field_name, value)
            else:
                raise ValueError(f"Invalid value for {field_name}: {message}")
    
    return instance