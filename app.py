"""NiceGUI frontend for the user's adaptive-notch algorithm."""
import asyncio
import base64
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from nicegui import ui
from core import process_wav
from updater import check_updates, install_updates, UpdateError

ui.dark_mode().enable()
with ui.column().classes('w-full max-w-5xl mx-auto p-6 gap-4'):
    ui.label('Nettoyage WAV · Notch adaptatif').classes('text-2xl font-bold')
    ui.label('Algorithme original : suivi temporel de la fréquence, de la largeur et de l’atténuation.').classes('text-gray-400')
    with ui.tabs().classes('w-full') as tabs:
        traitement=ui.tab('Traitement')
        reglages=ui.tab('Réglages avancés')
        aide=ui.tab('Aide')
        mises_a_jour=ui.tab('Mises à jour')
    with ui.tab_panels(tabs, value=traitement).classes('w-full'):
        with ui.tab_panel(traitement):
            mode=ui.toggle({'file': 'Fichier WAV', 'folder': 'Répertoire'}, value='file')
            with ui.column().classes('w-full') as file_fields:
                wav=ui.input('Chemin du WAV', placeholder=r'C:\WAV\enregistrement.wav').classes('w-full')
                output=ui.input('Sortie facultative', placeholder='Par défaut : *_clean.wav (aucun écrasement)').classes('w-full')
            with ui.column().classes('w-full') as folder_fields:
                with ui.row().classes('w-full items-end'):
                    folder=ui.input('Répertoire source', placeholder=r'C:\WAV\Session_01').classes('flex-grow')
                    async def browse_folder():
                        def choose():
                            root = tk.Tk()
                            root.withdraw()
                            root.attributes('-topmost', True)
                            try:
                                return filedialog.askdirectory(parent=root, title='Sélectionner le dossier WAV', initialdir=folder.value if folder.value and Path(folder.value).is_dir() else None)
                            finally:
                                root.destroy()
                        try:
                            selected=await asyncio.to_thread(choose)
                            if selected:
                                folder.value=selected
                        except Exception as exc:
                            ui.notify(f'Sélection indisponible : {exc}. Saisir le chemin manuellement.', type='warning')
                    ui.button('Parcourir…', icon='folder_open', on_click=browse_folder)
                ui.label('Tous les fichiers .wav du dossier (sans les sous-dossiers). Sorties dans un sous-dossier « nettoyes ».').classes('text-gray-400 text-sm')
            folder_fields.set_visibility(False)
            def switch_mode(e):
                file_fields.set_visibility(e.value == 'file')
                folder_fields.set_visibility(e.value == 'folder')
            mode.on_value_change(switch_mode)
            with ui.row().classes('gap-3'):
                n=ui.number('Oscillations recherchées', value=10, min=1, max=20, precision=0)
                fmin=ui.number('Fréquence min. (Hz)', value=1000, min=0)
                fmax=ui.number('Fréquence max. (Hz, 0 = automatique)', value=0, min=0)
            with ui.row().classes('gap-3 items-end'):
                correction=ui.number('Facteur de correction', value=1.0, min=0, max=2, step=0.05, format='%.2f').tooltip('1 = correction calculée ; 0.75 = plus douce ; >1 = plus forte').classes('w-48')
            status=ui.label('Prêt.')
            results=ui.column().classes('w-full gap-2')
        with ui.tab_panel(reglages):
            ui.label('Valeurs reprises du dernier appel de ton notebook Colab.').classes('text-gray-400')
            with ui.row().classes('gap-3'):
                peak_distance=ui.number('Distance min. des pics (Hz)',value=500,min=1)
                tracking_snr=ui.number('SNR min. suivi (dB)',value=3)
                valid_ratio=ui.number('Présence globale min. (0–1)',value=0.80,min=0,max=1,step=0.05)
            full_duration=ui.checkbox('Présence sur toute la durée obligatoire',value=True)
            with ui.row().classes('gap-3'):
                segments=ui.number('Nombre de segments',value=20,min=1,precision=0)
                segment_ratio=ui.number('Présence min. / segment',value=0.90,min=0,max=1,step=0.05)
            with ui.row().classes('gap-3'):
                max_range=ui.number('Dérive totale max. (Hz)',value=2500,min=0)
                max_dfdt=ui.number('Vitesse de dérive max. (Hz/s)',value=3000,min=0)
            with ui.row().classes('gap-3'):
                min_width=ui.number('Largeur notch min. (Hz)',value=80,min=1)
                max_width=ui.number('Largeur notch max. (Hz)',value=1200,min=1)
                margin=ui.number('Marge (Hz)',value=80,min=0)
            with ui.row().classes('gap-3'):
                attenuation=ui.number('Atténuation max. (dB)',value=45,min=0)
                min_excess=ui.number('Excès min. (dB)',value=3,min=0)
                target_margin=ui.number('Marge cible (dB)',value=2,min=0)
            with ui.row().classes('gap-3'):
                adjacent_inner=ui.number('Bruit adjacent : marge interne (Hz)',value=1000,min=0)
                adjacent_outer=ui.number('Bruit adjacent : marge externe (Hz)',value=3000,min=0)
                smoothing=ui.number('Lissage temporel (0–1)',value=0.85,min=0,max=1,step=0.05)
                residual_passes=ui.number('Passages résiduels',value=2,min=1,max=3,precision=0).tooltip('2 = remesure et corrige une seconde fois uniquement la raie résiduelle')
        with ui.tab_panel(aide):
            ui.markdown('''### Fonctionnement
**Paramètres principaux** : « Oscillations recherchées » est le nombre maximum de raies persistantes à détecter ; « Facteur de correction » règle la force de l'atténuation (1,0 par défaut). La détection utilise désormais la persistance temporelle afin de moins confondre les chirps transitoires avec des raies parasites. Ces réglages se trouvent dans l'onglet Traitement.\n\nLe script détecte les raies parasites globales, suit leur fréquence par STFT, teste leur présence et leur stabilité puis applique les masques notch temps-fréquence **canal par canal**. Il conserve l’original, produit un WAV nettoyé, un rapport CSV et une image des spectrogrammes.

**Garde-fous** : un pic absent ou trop instable peut être signalé sans être filtré. Vérifie les spectrogrammes, particulièrement en présence de cris de chauves-souris proches des fréquences parasites.

**Mode Répertoire** : sélectionner un dossier ou saisir son chemin. Tous les WAV du dossier (non récursif) sont traités avec les mêmes réglages. Les résultats sont créés dans `nettoyes`, sans écraser les fichiers existants. Les erreurs sur un fichier n’interrompent pas les suivants.\n\n**Fichiers produits** : `*_clean.wav`, `*_clean_report.csv`, éventuellement `*_clean_correlation.csv`, `*_clean_summary.json`, `*_clean_spectrogrammes.png`.

**Important** : l’analyse se déroule en mémoire. Sur de très longs WAV, le besoin en RAM peut être important. La première exécution via uv installe les dépendances. Aucun fichier existant n’est écrasé.''')

        with ui.tab_panel(mises_a_jour):
            ui.label('Mises à jour GitHub').classes('text-xl font-bold')
            ui.markdown('Le bouton vérifie uniquement la branche GitHub suivie par ton installation. Aucune modification locale ne sera écrasée. Une installation depuis un ZIP doit d’abord être remplacée par un **git clone**.')
            update_status=ui.label('Aucune vérification effectuée.')
            update_changes=ui.markdown('')
            install_button=ui.button('Installer la mise à jour', icon='download')
            install_button.disable()

            async def check_for_updates():
                check_button.disable()
                install_button.disable()
                update_status.text='Recherche des mises à jour...'
                try:
                    info=await asyncio.to_thread(check_updates)
                    if info['available']:
                        update_status.text=f"{info['commits']} nouveau(x) commit(s) disponible(s)."
                        update_changes.content='**Changements :**\n\n'+'\n'.join('- '+line for line in info['history'].splitlines())
                        install_button.enable()
                    else:
                        update_status.text='L’application est à jour.'
                        update_changes.content=''
                except UpdateError as exc:
                    update_status.text=str(exc)
                    update_changes.content=''
                finally:
                    check_button.enable()

            async def apply_update():
                with ui.dialog() as dialog, ui.card():
                    ui.label('Installer la mise à jour ?').classes('text-lg font-bold')
                    ui.label('Le programme devra être fermé puis relancé après téléchargement. Les traitements WAV ne doivent pas être en cours.')
                    with ui.row():
                        ui.button('Annuler', on_click=lambda: dialog.submit(False))
                        ui.button('Confirmer', on_click=lambda: dialog.submit(True))
                if not await dialog:
                    return
                if button.enabled is False:
                    ui.notify('Attends la fin du traitement WAV.', type='warning')
                    return
                check_button.disable()
                install_button.disable()
                update_status.text='Installation en cours...'
                try:
                    message=await asyncio.to_thread(install_updates)
                    update_status.text=message
                    ui.notify('Mise à jour installée : redémarrage manuel nécessaire.', type='positive')
                except UpdateError as exc:
                    update_status.text=str(exc)
                    ui.notify(str(exc), type='negative', timeout=12000)
                finally:
                    check_button.enable()

            check_button=ui.button('Vérifier les mises à jour', icon='refresh', on_click=check_for_updates)
            install_button.on_click(apply_update)

    def parameters():
        return dict(n_notches=int(n.value), fmin=float(fmin.value), fmax=None if not fmax.value else float(fmax.value),
            min_peak_distance_hz=float(peak_distance.value), min_tracking_snr_db=float(tracking_snr.value),
            min_valid_ratio=float(valid_ratio.value),require_full_duration_presence=bool(full_duration.value),
            presence_n_segments=int(segments.value),presence_min_valid_ratio_per_segment=float(segment_ratio.value),
            max_freq_range_hz=float(max_range.value),max_dfdt_p95_hz_s=float(max_dfdt.value),
            min_notch_width_hz=float(min_width.value),max_notch_width_hz=float(max_width.value),
            notch_margin_hz=float(margin.value), max_attenuation_db=float(attenuation.value),
            min_excess_db=float(min_excess.value),target_margin_db=float(target_margin.value),
            notch_correction_factor=float(correction.value),adjacent_inner_margin_hz=float(adjacent_inner.value),
            adjacent_outer_margin_hz=float(adjacent_outer.value),attenuation_smoothing_alpha=float(smoothing.value),
            residual_passes=int(residual_passes.value))

    def show_single(ret):
        with results:
            ui.label('WAV nettoyé : '+ret['output']).classes('text-green-400')
            ui.label('Rapport : '+ret['report'])
            ui.label('Spectrogrammes avant / après (mêmes axes et échelle de couleurs)').classes('text-lg font-bold')
            ui.image('data:image/png;base64,' + base64.b64encode(Path(ret['plot']).read_bytes()).decode('ascii')).classes('w-full rounded shadow')
            ui.label('Image enregistrée : ' + ret['plot']).classes('text-gray-400 text-sm')
            if ret['rows']:
                cols=[{'name':k,'label':k,'field':k} for k in ['notch','f0_global_hz','valid_ratio','present_full_duration','filter_applied']]
                ui.table(columns=cols,rows=ret['rows'],row_key='notch').classes('w-full')

    async def start():
        batch=mode.value=='folder'
        source=Path((folder.value if batch else wav.value).strip().strip('"')).expanduser()
        if batch and not source.is_dir():
            ui.notify('Répertoire introuvable.',type='negative'); return
        if not batch and not source.is_file():
            ui.notify('Fichier WAV introuvable.',type='negative'); return
        files=sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower()=='.wav') if batch else [source]
        if not files:
            ui.notify('Aucun fichier WAV dans ce répertoire.',type='warning'); return
        args=parameters()
        button.disable()
        results.clear()
        progress.set_visibility(batch)
        progress.value=0
        successes, skipped, failures=[],[],[]
        try:
            outdir=source / 'nettoyes' if batch else None
            if batch:
                outdir.mkdir(exist_ok=True)
            for i, item in enumerate(files, start=1):
                status.text=f'Traitement {i}/{len(files)} : {item.name}'
                target=outdir / (item.stem+'_clean.wav') if batch else (output.value.strip().strip('"') or None)
                try:
                    ret=await asyncio.to_thread(process_wav,item,target,**args)
                    successes.append((item.name,ret))
                except FileExistsError as exc:
                    skipped.append((item.name,str(exc)))
                except Exception as exc:
                    failures.append((item.name,str(exc)))
                progress.value=i/len(files)
                await asyncio.sleep(0)
            if batch:
                status.text=f'Terminé : {len(successes)} nettoyé(s), {len(skipped)} ignoré(s), {len(failures)} erreur(s).'
                with results:
                    ui.label(f'Résultats enregistrés dans : {outdir}').classes('text-green-400')
                    rows=([{'file':name,'state':'Nettoyé','detail':str(ret['output'])} for name,ret in successes]
                        +[{'file':name,'state':'Ignoré (sortie existante)','detail':error} for name,error in skipped]
                        +[{'file':name,'state':'Erreur','detail':error} for name,error in failures])
                    ui.table(columns=[{'name':k,'label':v,'field':k} for k,v in [('file','Fichier'),('state','Statut'),('detail','Détail')]],rows=rows,row_key='file').classes('w-full')
                    if successes:
                        ui.label('Spectrogrammes du dernier fichier nettoyé').classes('text-lg font-bold')
                        ui.image('data:image/png;base64,'+base64.b64encode(Path(successes[-1][1]['plot']).read_bytes()).decode('ascii')).classes('w-full rounded shadow')
            elif successes:
                status.text='Terminé.'
                show_single(successes[0][1])
            else:
                status.text='Aucun fichier traité.'
                with results:
                    for name,error in failures+skipped:
                        ui.label(f'{name} : {error}').classes('text-red-400')
        except Exception as exc:
            status.text=f'Erreur : {exc}'
            ui.notify(str(exc),type='negative',timeout=10000)
        finally:
            button.enable()

    progress=ui.linear_progress(value=0).classes('w-full')
    progress.set_visibility(False)
    button=ui.button('Démarrer le nettoyage',icon='play_arrow',on_click=start)

ui.run(title='Nettoyage WAV adaptatif',native=True,window_size=(1130,830),reload=False)
