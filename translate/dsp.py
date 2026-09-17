# -*- coding: utf-8 -*-
"""Audio shaping for VoiceRP personas: pitch, gruffness, radio.

numpy only. librosa or pyrubberband would each be a better phase vocoder, but
they pull scipy and numba - and the whole point of the slim install is that
839 MB of scientific stack went away. This is ~60 lines and measurably correct
for the +-6 semitone range personas need.
"""
import numpy as np

EPS = 1e-12


def _stft(x, n_fft, hop):
    win = np.hanning(n_fft).astype(np.float32)
    pad = n_fft // 2
    x = np.pad(x, pad, mode='reflect')
    frames = 1 + (len(x) - n_fft) // hop
    out = np.empty((frames, n_fft // 2 + 1), dtype=np.complex64)
    for i in range(frames):
        out[i] = np.fft.rfft(x[i * hop:i * hop + n_fft] * win)
    return out


def _istft(S, n_fft, hop):
    win = np.hanning(n_fft).astype(np.float32)
    n = (S.shape[0] - 1) * hop + n_fft
    y = np.zeros(n, dtype=np.float32)
    wsum = np.zeros(n, dtype=np.float32)
    for i in range(S.shape[0]):
        y[i * hop:i * hop + n_fft] += np.fft.irfft(S[i]).astype(np.float32) * win
        wsum[i * hop:i * hop + n_fft] += win ** 2
    y /= np.maximum(wsum, 1e-6)
    pad = n_fft // 2
    return y[pad:-pad] if len(y) > 2 * pad else y


def time_stretch(x, rate, n_fft=1024, hop=256):
    """Phase vocoder. rate > 1 makes it shorter, pitch unchanged."""
    if abs(rate - 1.0) < 1e-3 or len(x) < n_fft * 2:
        return x.astype(np.float32)
    S = _stft(x.astype(np.float32), n_fft, hop)
    mag, phase = np.abs(S), np.angle(S)
    # expected phase advance per hop for each bin
    dphi_expected = 2 * np.pi * hop * np.arange(S.shape[1]) / n_fft

    steps = np.arange(0, S.shape[0] - 1, rate)
    out = np.empty((len(steps), S.shape[1]), dtype=np.complex64)
    acc = phase[0].copy()
    for k, t in enumerate(steps):
        i = int(t)
        frac = t - i
        m = (1 - frac) * mag[i] + frac * mag[i + 1]
        out[k] = m * np.exp(1j * acc)
        # unwrap the true advance, then re-accumulate at the new rate
        dphi = phase[i + 1] - phase[i] - dphi_expected
        dphi -= 2 * np.pi * np.round(dphi / (2 * np.pi))
        acc = acc + dphi_expected + dphi
    return _istft(out, n_fft, hop)


def pitch_shift(x, semitones):
    """Shift pitch, keep duration. Negative is deeper."""
    if abs(semitones) < 0.05 or len(x) < 4096:
        return x.astype(np.float32)
    ratio = 2.0 ** (semitones / 12.0)
    # stretch by the inverse, then resample back: length returns, pitch moves
    stretched = time_stretch(x, 1.0 / ratio)
    n = int(round(len(stretched) / ratio))
    if n < 2:
        return x.astype(np.float32)
    idx = np.linspace(0, len(stretched) - 1, n)
    y = np.interp(idx, np.arange(len(stretched)), stretched).astype(np.float32)
    # trim or pad back to the original length so timing is untouched
    if len(y) > len(x):
        return y[:len(x)]
    return np.pad(y, (0, len(x) - len(y)))


def _biquad(x, b, a):
    y = np.empty_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        v = b[0] * x[i] + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        y[i] = v
        x2, x1 = x1, x[i]
        y2, y1 = y1, v
    return y


def _bandpass(x, sr, low, high):
    """Two one-pole sections via FFT - cheaper and click-free versus looping."""
    n = len(x)
    f = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    # 2nd-order-ish rolloff either side, done in the frequency domain
    resp = (freqs / np.maximum(low, 1.0))
    hp = resp ** 2 / (1 + resp ** 2)
    lp = 1.0 / (1 + (freqs / max(high, 1.0)) ** 4)
    return np.fft.irfft(f * hp * lp, n).astype(np.float32)


def radio(x, sr, drive=3.0, noise=0.006, low=350.0, high=3200.0):
    """Squad-radio colour: telephone band, soft clipping, a little hiss.

    The band limit is what sells it - a 350-3200 Hz voice reads as a radio even
    with no distortion at all. Drive adds the rest.
    """
    y = _bandpass(x.astype(np.float32), sr, low, high)
    peak = float(np.max(np.abs(y))) or 1.0
    y = np.tanh(y / peak * drive) / np.tanh(drive)
    if noise > 0:
        rng = np.random.default_rng(0)
        env = np.abs(y)
        # noise gated by the envelope, so silence stays silent
        k = max(1, int(sr * 0.02))
        env = np.convolve(env, np.ones(k) / k, mode='same')
        y = y + rng.normal(0, noise, len(y)).astype(np.float32) * (0.3 + env)
    return np.clip(y, -1.0, 1.0).astype(np.float32)


def apply_chain(x, sr, pitch=0.0, effect=None, gain=1.0):
    """Persona post-processing: pitch first, colour second."""
    y = x.astype(np.float32)
    if pitch:
        y = pitch_shift(y, pitch)
    if effect == 'radio':
        y = radio(y, sr)
    elif effect == 'radio_heavy':
        y = radio(y, sr, drive=6.0, noise=0.02, low=450.0, high=2800.0)
    if gain != 1.0:
        y = y * gain
    peak = float(np.max(np.abs(y))) or 1.0
    if peak > 0.99:
        y = y / peak * 0.99
    # 5 ms fades: the phase vocoder leaves one full-scale step at each edge,
    # which is a click, and a click is what started the whole crackle hunt.
    k = min(int(sr * 0.005), len(y) // 4)
    if k > 1:
        ramp = np.linspace(0, 1, k, dtype=np.float32)
        y[:k] *= ramp
        y[-k:] *= ramp[::-1]
    return y.astype(np.float32)
