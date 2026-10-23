"""Regression check: suppress slow line drift while protecting a brief chirp."""
import unittest
import numpy as np
from scipy import signal as sig
from scipy.ndimage import median_filter
from spectral_floor import spectral_floor_clean_stft


class SpectralFloorTest(unittest.TestCase):
    def test_slow_drift_removed_and_chirp_preserved(self):
        sr = 192000
        t = np.arange(int(2.4 * sr)) / sr
        rng = np.random.default_rng(107)
        f_line = 50880 + 40 * np.sin(2 * np.pi * t / 2.0)
        interference = 0.01 * np.sin(2 * np.pi * np.cumsum(f_line) / sr)
        gate = np.zeros_like(t)
        on = (t >= 1.15) & (t <= 1.19)
        gate[on] = np.hanning(np.count_nonzero(on))
        time_chirp = t - 1.15
        chirp = 0.05 * gate * np.sin(
            2 * np.pi * (32000 * time_chirp + 50000 * time_chirp ** 2)
        )
        x = interference + chirp + rng.normal(0, 0.0002, len(t))

        fft, hop = 32768, 8192
        f, ts, Z = sig.stft(
            x, fs=sr, nperseg=fft, noverlap=fft-hop,
            boundary="zeros", padded=True
        )
        near = np.where(np.abs(f - 50880) < 300)[0]
        centers = median_filter(
            near[np.argmax(np.abs(Z[near]), axis=0)],
            size=7, mode="nearest"
        )
        track = {
            "f0":50880, "t":ts, "freq":f[centers],
            "valid":np.ones(len(ts), dtype=bool),
        }
        clean_Z = spectral_floor_clean_stft(Z.copy(), f, ts, [track], [True])
        y = sig.istft(
            clean_Z, fs=sr, nperseg=fft,
            noverlap=fft-hop, boundary=True
        )[1][:len(x)]
        _, _, check_Z = sig.stft(
            y, fs=sr, nperseg=fft, noverlap=fft-hop,
            boundary="zeros", padded=True
        )
        center = (f >= 50750) & (f <= 51000)
        before = np.max(np.median(np.abs(Z[center]), axis=1))
        after = np.max(np.median(np.abs(check_Z[center]), axis=1))
        reduction_db = 20 * np.log10((after + 1e-30) / (before + 1e-30))
        self.assertLess(reduction_db, -20)

        band = sig.butter(4, [30000, 40000], btype="bandpass",
                          fs=sr, output="sos")
        xin = sig.sosfilt(band, x)
        yout = sig.sosfilt(band, y)
        change_db = 10 * np.log10(
            (np.sum(yout**2) + 1e-30) / (np.sum(xin**2) + 1e-30)
        )
        self.assertLess(abs(change_db), 0.05)


if __name__ == "__main__":
    unittest.main()
