"""程序化音效合成模块

所有音效在启动时用正弦/噪声包络实时合成，不依赖任何二进制音频资源。
"""
import array
import math
import random

import pygame

from config import get as cfg_get

_SAMPLE_RATE = 22050


def _sine_buffer(freq, duration, volume=0.5, decay=6.0, freq_end=None):
    """生成带指数衰减包络的正弦波（可选滑音）"""
    n = max(1, int(_SAMPLE_RATE * duration))
    buf = array.array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        f = freq if freq_end is None else freq + (freq_end - freq) * t
        phase += 2.0 * math.pi * f / _SAMPLE_RATE
        env = math.exp(-decay * t)
        buf.append(int(32767 * volume * env * math.sin(phase)))
    return buf


def _noise_buffer(duration, volume=0.5, decay=8.0, lowpass=0.35):
    """生成带衰减的低通噪声（用于枪声/爆炸）"""
    n = max(1, int(_SAMPLE_RATE * duration))
    buf = array.array("h")
    last = 0.0
    for i in range(n):
        t = i / n
        sample = random.uniform(-1.0, 1.0)
        last = last + lowpass * (sample - last)
        env = math.exp(-decay * t)
        buf.append(int(32767 * volume * env * last * 2.2))
    return buf


def _click_buffer(duration=0.03, volume=0.4):
    """短促点击声（换弹/UI）"""
    n = max(1, int(_SAMPLE_RATE * duration))
    buf = array.array("h")
    for i in range(n):
        t = i / n
        env = math.exp(-40.0 * t)
        buf.append(int(32767 * volume * env * math.sin(2 * math.pi * 2200 * i / _SAMPLE_RATE)))
    return buf

def _mix(*bufs):
    """å°å¤ä¸ªé³é¢ç¼å²åæä¸ä¸ª（é²æ­¢æº¢åºï¼"""
    n = max(len(b) for b in bufs)
    out = array.array("h", [0]) * n
    for b in bufs:
        for i, s in enumerate(b):
            v = out[i] + s
            out[i] = max(-32768, min(32767, v))
    return out



class AudioManager:
    """全局音效管理器（单例），mixer 初始化失败时静默降级"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.available = False
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=1)
        except pygame.error:
            return
        self.available = True
        self._build_sounds()

    def _build_sounds(self):
        def make(buf):
            return pygame.mixer.Sound(buffer=buf)

        self.sounds = {
            "shoot": make(_noise_buffer(0.09, volume=0.55, decay=22.0)),
            "hit": make(_sine_buffer(1250, 0.07, volume=0.4, decay=18.0)),
            "kill": make(_sine_buffer(660, 0.16, volume=0.45, decay=8.0, freq_end=1320)),
            "explosion": make(_noise_buffer(0.55, volume=0.8, decay=5.0, lowpass=0.18)),
            "pickup": make(_sine_buffer(520, 0.14, volume=0.4, decay=7.0, freq_end=1040)),
            "reload": make(_click_buffer(0.05, volume=0.5)),
            "melee": make(_noise_buffer(0.12, volume=0.4, decay=14.0, lowpass=0.5)),
            "ui_click": make(_click_buffer(0.04, volume=0.35)),
            "door_open": make(_sine_buffer(160, 0.30, volume=0.35, decay=4.0, freq_end=320)),
            "door_close": make(_sine_buffer(300, 0.25, volume=0.35, decay=5.0, freq_end=150)),
            "door_slam": make(_mix(
                _noise_buffer(0.16, volume=0.55, decay=22.0, lowpass=0.15),
                _sine_buffer(85, 0.22, volume=0.5, decay=12.0))),
        }

    def master_volume(self):
        try:
            v = float(cfg_get("audio.volume", 80))
        except (TypeError, ValueError):
            v = 80.0
        return max(0.0, min(1.0, v / 100.0))

    def play(self, name, volume=1.0, pos=None, listener_pos=None, max_dist=900.0):
        """播放音效；pos/listener_pos 同时给出时按距离衰减"""
        if not self.available:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        vol = self.master_volume() * max(0.0, min(1.0, volume))
        if pos is not None and listener_pos is not None:
            try:
                dist = (pygame.Vector2(pos) - pygame.Vector2(listener_pos)).length()
            except (TypeError, ValueError):
                dist = 0.0
            vol *= max(0.0, 1.0 - dist / max_dist)
        if vol <= 0.01:
            return
        sound.set_volume(vol)
        sound.play()


audio = AudioManager()
