from dataclasses import dataclass

@dataclass
class settings_type:
    SAMPLE_RATE : int
    MAX_GAIN : float
    WHOLE_NOTE : float
    PITCH_INTERP_VEL : float
    GAIN_INTERP_VEL : float
    BASE_PITCH : float
    NOTES : dict[str, float]
    MODIFIERS : dict[str, float]

def get_default_settings():
    return settings_type(
        SAMPLE_RATE=44100,
        MAX_GAIN=3000.0,
        WHOLE_NOTE=1.6,
        PITCH_INTERP_VEL=0.001,
        GAIN_INTERP_VEL=0.01,
        BASE_PITCH=440.0,
        NOTES={
            'A': 1,
            'As': 16/15, 
            'B': 9/8,
            'C': 6/5,
            'Cs': 5/4,
            'D': 4/3,
            'Ds': 7/5,
            'E': 3/2,
            'F': 8/5,
            'Fs': 5/3,
            'G': 7/4,
            'Gs': 15/8, 
        },
        MODIFIERS={
            '-': 1/2,
            '+': 2,
        },
    )