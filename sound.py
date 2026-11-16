"""Procedurally generated sound effects (no audio files needed)."""

import math
from array import array

import pygame

from config import SOUND_VOLUME

# name: (list of (frequency in Hz, duration in seconds), relative volume)
SOUND_DEFINITIONS = {
    "deliver": ([(880, 0.09), (1320, 0.14)], 0.55),
    "build": ([(523, 0.07), (784, 0.12)], 0.7),
    "remove": ([(523, 0.07), (392, 0.12)], 0.6),
    "train": ([(330, 0.06), (440, 0.06), (660, 0.14)], 0.7),
    "click": ([(660, 0.05)], 0.5),
    "error": ([(196, 0.09), (175, 0.14)], 0.7),
    "warning": ([(740, 0.09), (0, 0.05), (740, 0.12)], 0.6),
    "miss": ([(233, 0.12), (175, 0.22)], 0.9),
    "gameover": ([(392, 0.18), (330, 0.18), (262, 0.18), (196, 0.45)], 1.0),
}


def _synthesise(notes, volume, sample_rate, channels):
    samples = array("h")
    for frequency, duration in notes:
        count = int(sample_rate * duration)
        for index in range(count):
            if not frequency:
                value = 0.0
            else:
                moment = index / sample_rate
                attack = min(1.0, index / (sample_rate * 0.004))
                envelope = attack * math.exp(-5.0 * index / count)
                wave = math.sin(math.tau * frequency * moment)
                wave += 0.25 * math.sin(math.tau * frequency * 2 * moment)
                value = volume * envelope * wave / 1.25
            samples.extend([int(32767 * value)] * channels)
    return pygame.mixer.Sound(buffer=samples.tobytes())


class Sounds:
    def __init__(self):
        self.muted = False
        self.sounds = {}
        self.last_played = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sample_rate, sample_format, channels = pygame.mixer.get_init()
            if sample_format != -16:
                return
            for name, (notes, volume) in SOUND_DEFINITIONS.items():
                self.sounds[name] = _synthesise(notes, volume * SOUND_VOLUME, sample_rate, channels)
        except (pygame.error, TypeError):
            self.sounds = {}

    @property
    def available(self):
        return bool(self.sounds)

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted

    def play(self, name, min_gap=0.06):
        sound = self.sounds.get(name)
        if sound is None or self.muted:
            return
        now = pygame.time.get_ticks() / 1000.0
        if now - self.last_played.get(name, -10.0) < min_gap:
            return
        self.last_played[name] = now
        sound.play()
