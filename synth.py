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

async def get_samples(notes : list[str], settings : settings_type) -> list[int]:
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

import random
from scipy.fft import fft, ifft
from scipy.stats import norm
#import matplotlib.pyplot as plt

def get_noise_samples(settings : settings_type, pitch : float, dev : float) -> list[int]:
    min_gain = int(-1 * settings.MAX_GAIN)
    max_gain = int(settings.MAX_GAIN)
    n = settings.SAMPLE_RATE // 2
    samples = [random.randint(min_gain, max_gain) for _ in range(n)]
    freqs = fft(samples)
    freqs *= [dev * norm.pdf(x, loc=pitch, scale=dev) for x in range(n)]

    #plt.plot(abs(freqs)) # type: ignore
    #plt.show() # type: ignore

    samples = [int(abs(x)) for x in ifft(freqs)]
    return samples

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