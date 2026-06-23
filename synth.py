import math
from default_settings import settings_type
import utils

def note_lexer(note : str):
    numbers = ''.join([c for c in note if c.isnumeric()])
    letters = ''.join([c for c in note if c.isalpha()])
    other = ''.join([c for c in note if not c.isalnum()])
    return numbers, letters, other

def note_parser(numbers : str, letters : str, other : str, settings : settings_type, duration : float):
    hz = settings.BASE_PITCH * settings.NOTES.get(letters, 0)
    for modifier in other:
        hz *= settings.MODIFIERS.get(modifier, 1)
    duration = settings.WHOLE_NOTE / int(numbers) if numbers else duration
    return hz, duration

def get_samples(notes : list[str], settings : settings_type) -> list[int]:
    def wave_fn(x : float, gain : float):
        total = 0
        for overtone in settings.OVERTONES:
            total += settings.OVERTONES[overtone] * math.sin(utils.parse_num(overtone) * x)
        out = int(total * gain * settings.MAX_GAIN)
        return int(settings.MAX_GAIN) if out > settings.MAX_GAIN else int(-settings.MAX_GAIN) if out < -settings.MAX_GAIN else out
    
    x = 0
    dx = 0
    gain = 1
    hz = 0
    duration = settings.WHOLE_NOTE / 8
    samples : list[int] = []

    i = 0
    samples_left = 0
    while i < len(notes) or samples_left > 0:
        if samples_left == 0:
            numbers, letters, other = note_lexer(notes[i])
            hz, duration = note_parser(numbers, letters, other, settings, duration)

            samples_left = int(settings.SAMPLE_RATE * duration)
            i += 1
        
        dx_target = 2 * math.pi * hz / settings.SAMPLE_RATE
        dx = (1 - settings.PITCH_INTERP_VEL) * dx + settings.PITCH_INTERP_VEL * dx_target
        x += dx

        gain_target = 0 if hz == 0 else 1
        gain = (1 - settings.GAIN_INTERP_VEL) * gain + settings.GAIN_INTERP_VEL * gain_target

        samples.append(wave_fn(x, gain))
        samples_left -= 1
        
    return samples

import numpy
from scipy.signal import ShortTimeFFT, get_window
import random

def formant_curve(hz : int, peak : int, spread : int):
    return max(spread - abs(hz - peak), 0)

FORMANTS : dict[str, list[int]] = {
    'a': [764, 1322],
    'e': [526, 2002],
    'i': [301, 2338],
    'o': [505, 986],
    'u': [309, 1047],
    'm': [300, 1250, 2500],
    'n': [300, 1250, 3000],
    'p': [1750],
    't': [3000],
    'k': [2250],
    's': [5500],
    'w': [309, 1047],
    'j': [301, 2338],
    'l': [350],
}

DURATIONS : dict[str, float] = {
    'a': 0.3,
    'e': 0.3,
    'i': 0.3,
    'o': 0.3,
    'u': 0.3,
    'm': 0.1,
    'n': 0.1,
    'p': 0.1,
    't': 0.1,
    'k': 0.1,
    's': 0.1,
    'w': 0.1,
    'j': 0.1,
    'l': 0.1,
}

def get_noise_samples(settings : settings_type, ipa : str, spread : int, win_size : int, hop : int) -> list[int]:
    pre_samples : list[float] = []
    vowel_table : list[str] = []
    for phoneme in ipa:
        num_samples = int(DURATIONS[phoneme] * settings.SAMPLE_RATE)
        for x in range(num_samples):
            if phoneme == 'p' or phoneme == 't' or phoneme == 'k':
                sample = 0 #???
            elif phoneme == 's':
                sample = random.randrange(0, int(settings.BASE_PITCH))
            else:
                sample = x % settings.BASE_PITCH
            pre_samples.append(sample)
            vowel_table.append(phoneme)

    STFFT = ShortTimeFFT(get_window('hann', win_size), hop, settings.SAMPLE_RATE)
    freqs = STFFT.stft(numpy.array(pre_samples))

    for i in range(len(freqs)):
        for j in range(len(freqs[i])):
            hz = STFFT.f[i]
            x = math.floor(STFFT.delta_t * j * settings.SAMPLE_RATE)
            if x >= len(vowel_table):
                continue
            phoneme = vowel_table[x]
            freqs[i][j] *= sum((formant_curve(hz, peak, spread) for peak in FORMANTS[phoneme]))

    post_samples = STFFT.istft(freqs).real
    post_samples_min = post_samples.min()
    samples = ((post_samples - post_samples_min) / (post_samples.max() - post_samples_min) - 0.5) * 2 * settings.MAX_GAIN
    return [int(x) for x in samples]

import wave
import io
from array import array

def buf_from_samples(samples : list[int], settings : settings_type):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1) # 1 channel
        wf.setsampwidth(2) # 16-bit
        wf.setframerate(settings.SAMPLE_RATE)

        frames = array('h', samples).tobytes() # h = signed 16 bit
        wf.writeframes(frames)

    buf.seek(0)
    return buf