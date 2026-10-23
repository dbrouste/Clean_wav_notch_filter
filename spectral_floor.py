"""Spectral-floor cleaner for verified slowly drifting interference lines.

Unlike a deep Gaussian notch, this algorithm attenuates each STFT bin only
towards a robust neighboring noise estimate. The caller must validate spectral
persistence and reject transient chirps before calling this helper.
"""
import numpy as np
from scipy.ndimage import median_filter


def spectral_floor_clean_stft(
    Z, freqs, times, tracks, enabled, *,
    target_margin_db=0.0,
    radius_hz=180.0,
    peak_search_hz=300.0,
    min_line_contrast_db=7.6,
):
    """Modify complex STFT Z in-place; return Z for convenience.

    The target is the per-frame STFT spectral floor, not a guaranteed
    time-domain attenuation level after inverse-STFT reconstruction.
    """
    if Z.ndim != 2 or len(freqs) != Z.shape[0] or len(times) != Z.shape[1]:
        raise ValueError("Inconsistent STFT shapes")
    if not np.isfinite(radius_hz) or radius_hz <= 0:
        raise ValueError("radius_hz must be positive")
    if not np.isfinite(target_margin_db):
        raise ValueError("target_margin_db must be finite")
    if len(freqs) < 3 or Z.shape[1] == 0:
        return Z

    df = float(freqs[1] - freqs[0])
    nfreq, nframes = Z.shape
    original_amplitude = np.abs(Z)
    search_bins = max(2, int(np.ceil(peak_search_hz / df)))
    minimum_ratio = 10.0 ** (min_line_contrast_db / 20.0)
    target_ratio = 10.0 ** (target_margin_db / 20.0)
    rad_bins = max(2, int(np.ceil(radius_hz / df)))
    inner_bins = max(rad_bins + 1, int(np.ceil(450.0 / df)))
    outer_bins = max(inner_bins + 4, int(np.ceil(1000.0 / df)))

    for track, apply in zip(tracks, enabled):
        if not apply:
            continue
        center = float(track["f0"])
        if not np.isfinite(center):
            continue
        k0 = int(np.clip(round(center / df), 1, nfreq - 2))
        indices = np.arange(max(1, k0 - search_bins), min(nfreq - 1, k0 + search_bins + 1))
        if len(indices) < 3:
            continue
        raw_centers = indices[np.argmax(original_amplitude[indices], axis=0)]
        centers = median_filter(raw_centers, size=7, mode="nearest")
        predicted = np.interp(times, track["t"], track["freq"])
        valid = np.interp(times, track["t"], track["valid"].astype(float)) > 0.5
        # An isolated loud chirp cannot pull the notch away from its track.
        plausible = np.abs(freqs[centers] - predicted) <= max(120.0, 3.0 * df)
        for j in range(nframes):
            if not valid[j] or not plausible[j]:
                continue
            k = int(centers[j])
            left = original_amplitude[max(0, k - outer_bins):max(0, k - inner_bins), j]
            right = original_amplitude[min(nfreq, k + inner_bins + 1):min(nfreq, k + outer_bins + 1), j]
            if len(left) < 4 or len(right) < 4:
                continue
            noise = float(np.median(np.concatenate((left, right))))
            if noise <= 0 or original_amplitude[k, j] < minimum_ratio * noise:
                continue
            lo = max(0, k - rad_bins)
            hi = min(nfreq, k + rad_bins + 1)
            magnitude = np.abs(Z[lo:hi, j])
            goal = noise * target_ratio
            Z[lo:hi, j] *= np.minimum(1.0, goal / (magnitude + 1e-30))
    return Z
