import math
from default_settings import defaults

def note_lexer(note):
    numbers = ''.join([c for c in note if c.isnumeric()])
    letters = ''.join([c for c in note if c.isalpha()])
    other = ''.join([c for c in note if not c.isalnum()])
    return numbers, letters, other

def note_parser(numbers, letters, other, settings, duration):
    hz = settings['BASE_PITCH'] * settings['NOTES'].get(letters, 0)
    for modifier in other:
        hz *= settings['MODIFIERS'].get(modifier, 1)
    duration = settings['WHOLE_NOTE'] / int(numbers) if numbers else duration
    return hz, duration

async def get_samples(notes, settings):
    x = 0
    dx = 0
    gain = 1
    duration = settings['WHOLE_NOTE'] / 8
    samples = []

    i = 0
    samples_left = 0
    while i < len(notes) or samples_left > 0:
        if samples_left == 0:
            numbers, letters, other = note_lexer(notes[i])
            hz, duration = note_parser(numbers, letters, other, settings, duration)

            samples_left = int(settings['SAMPLE_RATE'] * duration)
            i += 1
        
        dx_target = 2 * math.pi * hz / settings['SAMPLE_RATE']
        dx = (1 - settings['PITCH_INTERP_VEL']) * dx + settings['PITCH_INTERP_VEL'] * dx_target
        x += dx

        gain_target = 0 if hz == 0 else 1
        gain = (1 - settings['GAIN_INTERP_VEL']) * gain + settings['GAIN_INTERP_VEL'] * gain_target

        samples.append(int(math.sin(x) * gain * settings['MAX_GAIN']))
        samples_left -= 1
        
    return samples

import random

def get_noise_samples(settings):
    min_gain = -1 * settings['MAX_GAIN']
    max_gain = settings['MAX_GAIN']
    return [random.randint(min_gain, max_gain) for _ in range(settings['SAMPLE_RATE'])]

import wave
import io
from array import array

def buf_from_samples(samples, settings):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1) # 1 channel
        wf.setsampwidth(2) # 16-bit
        wf.setframerate(settings['SAMPLE_RATE'])

        frames = array('h', samples).tobytes() # h = signed 16 bit
        wf.writeframes(frames)

    buf.seek(0)
    return buf