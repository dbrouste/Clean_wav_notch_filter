"""Thin Windows adapter around the original Colab algorithm."""
from pathlib import Path
import json
import numpy as np
import soundfile as sf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import scipy.signal as sig
from filtre_notch_adaptatif import clean_wav_adaptive_notch


def process_wav(source, output=None, **kwargs):
    source = Path(source).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != '.wav':
        raise ValueError('Le fichier WAV est introuvable.')
    target = Path(output).expanduser().resolve() if output else source.with_name(source.stem + '_clean.wav')
    if source == target:
        raise ValueError('Le fichier de sortie doit être différent de l’original.')
    if target.exists():
        raise FileExistsError(f'Sortie existante : {target}. Change le nom pour éviter un écrasement.')
    if not target.parent.is_dir():
        raise ValueError('Le répertoire de sortie est introuvable.')
    info = sf.info(str(source))
    if info.frames < 2:
        raise ValueError('WAV trop court.')
    allowed_max = info.samplerate / 2
    fmin = float(kwargs.get('fmin', 1000))
    fmax = kwargs.get('fmax')
    if fmax is not None and not (fmin < float(fmax) < allowed_max):
        raise ValueError(f'La fréquence max. doit être comprise entre {fmin} Hz et {allowed_max:.0f} Hz.')
    x, y, sr, report, corr = clean_wav_adaptive_notch(str(source), verbose=False, **kwargs)
    # Preserve the original WAV encoding/subtype, including floating-point formats.
    sf.write(str(target), y, sr, format='WAV', subtype=info.subtype)
    csv = target.with_name(target.stem + '_report.csv')
    report.to_csv(csv, index=False)
    corr_csv = None
    if corr is not None:
        corr_csv = target.with_name(target.stem + '_correlation.csv')
        corr.to_csv(corr_csv)
    summary = target.with_name(target.stem + '_summary.json')
    summary.write_text(json.dumps({'source': str(source), 'output': str(target), 'parameters':kwargs,
        'sample_rate':sr, 'channels':int(x.shape[1]), 'duration_s':len(x)/sr,
        'detected':len(report), 'applied':int(report['filter_applied'].sum())}, indent=2, ensure_ascii=False),encoding='utf-8')
    # A lightweight plot for inspection; decimate displayed frames for large recordings.
    plot_path = target.with_name(target.stem + '_spectrogrammes.png')
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True, sharey=True, constrained_layout=True)
    nperseg = min(8192, len(x))
    for ax, data, caption in zip(axes, [x[:, 0], y[:, 0]], ['Entrée', 'Après nettoyage']):
        f,t,Z = sig.stft(data, fs=sr, nperseg=nperseg, noverlap=nperseg*3//4)
        keep = (f>=10000)&(f<=min(190000, sr/2))
        if len(t)>1500:
            step=max(1,len(t)//1500)
            Z=Z[:, ::step]
            t=t[::step]
        img=ax.pcolormesh(t,f[keep],20*np.log10(abs(Z[keep])+1e-12),vmin=-120,vmax=-30,shading='auto',cmap='viridis',rasterized=True)
        ax.set_ylabel('Fréquence (Hz)')
        ax.set_title(caption)
    axes[-1].set_xlabel('Temps (s)')
    fig.colorbar(img, ax=axes, label='Amplitude (dB)')
    fig.savefig(plot_path, dpi=120)
    plt.close(fig)
    return {'output':str(target),'report':str(csv),'correlation':str(corr_csv) if corr_csv else None,
            'summary':str(summary),'plot':str(plot_path),'rows':report.replace({np.nan: None}).to_dict(orient='records')}
