from ctypes import Structure, c_char, c_double, c_int
from dataclasses import dataclass, field

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