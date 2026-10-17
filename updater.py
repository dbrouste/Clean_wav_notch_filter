"""Conservative Git updater for a locally cloned application.

Never overwrites edits, never switches branch, never forces updates.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


class UpdateError(RuntimeError):
    pass


def git(*args):
    try:
        process = subprocess.run(
            ['git', *args], cwd=ROOT, capture_output=True, text=True,
            timeout=120, encoding='utf-8', errors='replace',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(f'Git indisponible ou délai dépassé : {exc}') from exc
    if process.returncode:
        raise UpdateError((process.stderr or process.stdout).strip() or 'Git a échoué.')
    return process.stdout.strip()


def verify_git_checkout():
    if not (ROOT / '.git').exists():
        raise UpdateError('Cette installation vient d’un ZIP. Pour activer les mises à jour, installe le dépôt avec git clone (voir README).')
    top = Path(git('rev-parse', '--show-toplevel')).resolve()
    if top != ROOT.resolve():
        raise UpdateError('Le dossier de l’application n’est pas la racine du dépôt Git.')
    if git('status', '--porcelain', '--untracked-files=normal'):
        raise UpdateError('Des fichiers locaux sont modifiés ou non suivis. Sauvegarde/committe-les avant la mise à jour.')
    branch = git('branch', '--show-current')
    if not branch:
        raise UpdateError('Branche Git détachée : mise à jour refusée.')
    upstream = git('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}')
    if not upstream.startswith('origin/'):
        raise UpdateError('La branche ne suit pas origin : mise à jour refusée.')
    return branch, upstream


def check_updates():
    branch, upstream = verify_git_checkout()
    git('fetch', '--prune', 'origin', branch)
    behind_ahead = git('rev-list', '--left-right', '--count', f'HEAD...{upstream}').split()
    behind, ahead = map(int, behind_ahead)
    if ahead:
        raise UpdateError('La branche locale contient des commits non publiés ; mise à jour automatique refusée.')
    history = git('log', '--format=%h %s', f'HEAD..{upstream}', '-8') if behind else ''
    return {'available': bool(behind), 'commits': behind, 'history': history,
            'branch': branch, 'upstream': upstream}


def install_updates():
    branch, upstream = verify_git_checkout()
    # Refuse a divergent local branch even if the user clicks during a concurrent change.
    git('merge', '--ff-only', upstream)
    # uv sync reuses the resolved dependency environment / lock file.
    try:
        p = subprocess.run(['uv', 'sync'], cwd=ROOT, capture_output=True,
                           text=True, timeout=300, encoding='utf-8', errors='replace',
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(f'Code actualisé, mais synchronisation des dépendances échouée : {exc}') from exc
    if p.returncode:
        raise UpdateError('Code actualisé, mais uv sync a échoué : '+(p.stderr or p.stdout)[-1500:])
    return 'Mise à jour installée. Ferme puis relance le logiciel pour utiliser la nouvelle version.'
