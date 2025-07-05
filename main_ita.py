#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitor_poll_menu.py v1.3.0

Strumento “self‐contained” in Python (solo stdlib) per monitorare
una o più directory tramite polling. Interfaccia a menu testuale,
con:

  • più directory configurabili  
  • scansione ricorsiva o non  
  • inclusione/esclusione dei nascosti  
  • filtri avanzati (glob include/exclude)  
  • logging su console e/o file  
  • rilevazione di creazione, cancellazione e modifica  
  • ESC per interrompere il monitor e tornare al menu

Nessuna dipendenza esterna: funziona con Python 3.6+ e solo librerie standard.
"""

import os
import sys
import time
import select
import logging
import fnmatch
import termios
import tty
from pathlib import Path

def scansiona_directory(bases, ricorsivo, includi_nascosti,
                         include_pats, exclude_pats):
    """
    Per ogni directory in 'bases', costruisce uno snapshot:
      { "base|percorso_relativo": timestamp_modifica }
    Applica pattern glob di include/exclude e rispetta l'opzione nascosti.
    """
    snapshot = {}
    for base in bases:
        base = base.resolve()
        if ricorsivo:
            for root, dirs, files in os.walk(base):
                if not includi_nascosti:
                    dirs[:]  = [d for d in dirs  if not d.startswith('.')]
                    files[:] = [f for f in files if not f.startswith('.')]
                # directory
                for d in dirs:
                    full = Path(root) / d
                    rel = full.relative_to(base).as_posix() + '/'
                    if _filtra(rel, include_pats, exclude_pats):
                        snapshot[f"{base}|{rel}"] = full.stat().st_mtime
                # file
                for f in files:
                    full = Path(root) / f
                    rel = full.relative_to(base).as_posix()
                    if _filtra(rel, include_pats, exclude_pats):
                        snapshot[f"{base}|{rel}"] = full.stat().st_mtime
        else:
            for child in base.iterdir():
                name = child.name
                if not includi_nascosti and name.startswith('.'):
                    continue
                rel = name + ('/' if child.is_dir() else '')
                if _filtra(rel, include_pats, exclude_pats):
                    snapshot[f"{base}|{rel}"] = child.stat().st_mtime
    return snapshot

def _filtra(name, includes, excludes):
    """
    Controlla se 'name' passa i filtri include/exclude (glob).
    """
    if includes and not any(fnmatch.fnmatch(name, p) for p in includes):
        return False
    if excludes and any(fnmatch.fnmatch(name, p) for p in excludes):
        return False
    return True

def confronta_snapshot(vecchio, nuovo):
    """
    Confronta due snapshot e ritorna tuple di:
      (aggiunti, rimossi, modificati)
    """
    old_keys = set(vecchio)
    new_keys = set(nuovo)
    aggiunti   = new_keys - old_keys
    rimossi    = old_keys - new_keys
    modificati = {k for k in old_keys & new_keys if vecchio[k] != nuovo[k]}
    return aggiunti, rimossi, modificati

def imposta_logging(file_log):
    """
    Configura logging su stdout e, se specificato, su file.
    """
    handlers = [logging.StreamHandler(sys.stdout)]
    if file_log:
        handlers.append(logging.FileHandler(file_log, encoding='utf-8'))
    fmt = "%(asctime)s %(levelname)-8s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)

def _abilita_modalità_raw():
    """
    Abilita cbreak su stdin per leggere ESC senza invio.
    Restituisce le vecchie impostazioni termios.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    return old

def _ripristina_modalità(old):
    """
    Ripristina le impostazioni termios originali.
    """
    fd = sys.stdin.fileno()
    termios.tcsetattr(fd, termios.TCSADRAIN, old)

def menu():
    """
    Mostra il menu di configurazione. Ritorna i parametri per il monitor.
    """
    dirs = []
    intervallo = 5.0
    ricorsivo = False
    includi_nascosti = False
    include_pats, exclude_pats = [], []
    file_log = None

    while True:
        print("\n" + "="*60)
        print("   MONITOR DIRECTORY VIA POLLING – VERSIONE 1.3.0")
        print("="*60)
        print("1) Aggiungi directory")
        print("2) Rimuovi directory")
        print("3) Mostra directory configurate")
        print(f"4) Intervallo polling:       {intervallo:.1f}s")
        print(f"5) Scansione ricorsiva:      {'SÌ' if ricorsivo else 'NO'}")
        print(f"6) Includi nascosti:         {'SÌ' if includi_nascosti else 'NO'}")
        print("7) Filtri avanzati (include/exclude)")
        print(f"8) File di log:             {file_log or 'stdout'}")
        print("9) Avvia monitoraggio")
        print("0) Esci")
        print("-"*60)
        scelta = input("Seleziona [0-9]: ").strip()

        if scelta == '1':
            p = input("   Inserisci directory da aggiungere: ").strip()
            d = Path(p).expanduser().resolve()
            if d.is_dir() and d not in dirs:
                dirs.append(d)
                print("   + Aggiunta:", d)
            else:
                print("   ! Percorso non valido o già presente")
        elif scelta == '2':
            if not dirs:
                print("   ! Nessuna directory da rimuovere")
            else:
                for i, d in enumerate(dirs, 1):
                    print(f"   {i}) {d}")
                v = input("   Numero da rimuovere: ").strip()
                if v.isdigit() and 1 <= int(v) <= len(dirs):
                    rim = dirs.pop(int(v)-1)
                    print("   - Rimossa:", rim)
                else:
                    print("   ! Selezione non valida")
        elif scelta == '3':
            if not dirs:
                print("   ! Nessuna directory configurata")
            else:
                print("   Directory configurate:")
                for d in dirs:
                    print("    -", d)
        elif scelta == '4':
            v = input("   Imposta intervallo (s): ").strip()
            try:
                intervallo = float(v)
            except ValueError:
                print("   ! Valore non valido")
        elif scelta == '5':
            ricorsivo = not ricorsivo
            print("   Ricorsiva:", "SÌ" if ricorsivo else "NO")
        elif scelta == '6':
            includi_nascosti = not includi_nascosti
            print("   Includi nascosti:", "SÌ" if includi_nascosti else "NO")
        elif scelta == '7':
            submenu_filtri(include_pats, exclude_pats)
        elif scelta == '8':
            v = input("   Percorso file di log (vuoto=stdout): ").strip()
            file_log = Path(v).expanduser().resolve() if v else None
        elif scelta == '9':
            if not dirs:
                print("   ! Aggiungi almeno una directory")
                continue
            return dirs, intervallo, ricorsivo, includi_nascosti, include_pats, exclude_pats, file_log
        elif scelta == '0':
            sys.exit(0)
        else:
            print("   ! Scelta non valida")

def submenu_filtri(includes, excludes):
    """
    Sottomenu per gestire pattern glob di include/exclude.
    """
    while True:
        print("\n  > FILTRI AVANZATI")
        print("  a) Aggiungi pattern INCLUDE")
        print("  b) Rimuovi pattern INCLUDE")
        print("  c) Mostra pattern INCLUDE")
        print("  d) Aggiungi pattern EXCLUDE")
        print("  e) Rimuovi pattern EXCLUDE")
        print("  f) Mostra pattern EXCLUDE")
        print("  x) Torna al menu principale")
        sel = input("  Seleziona [a-f,x]: ").strip().lower()
        if sel == 'a':
            p = input("    Inserisci pattern INCLUDE: ").strip()
            if p and p not in includes:
                includes.append(p); print("    +", p)
        elif sel == 'b':
            for i, p in enumerate(includes, 1):
                print(f"    {i}) {p}")
            v = input("    Numero da rimuovere: ").strip()
            if v.isdigit() and 1 <= int(v) <= len(includes):
                rem = includes.pop(int(v)-1); print("    -", rem)
        elif sel == 'c':
            print("    INCLUDE:", includes or ["(nessuno)"])
        elif sel == 'd':
            p = input("    Inserisci pattern EXCLUDE: ").strip()
            if p and p not in excludes:
                excludes.append(p); print("    +", p)
        elif sel == 'e':
            for i, p in enumerate(excludes, 1):
                print(f"    {i}) {p}")
            v = input("    Numero da rimuovere: ").strip()
            if v.isdigit() and 1 <= int(v) <= len(excludes):
                rem = excludes.pop(int(v)-1); print("    -", rem)
        elif sel == 'f':
            print("    EXCLUDE:", excludes or ["(nessuno)"])
        elif sel == 'x':
            break
        else:
            print("    ! Scelta non valida")

def ciclo_monitoring(paths, intervallo, ricorsivo, includi_nascosti,
                     include_pats, exclude_pats, file_log):
    """
    Loop di monitoraggio. Premere ESC per interrompere e tornare al menu.
    """
    imposta_logging(file_log)
    logging.info("==== Monitor avviato (premere ESC per tornare) ====")
    logging.info(f"Directory: {', '.join(str(p) for p in paths)}")
    logging.info(f"Intervallo: {intervallo}s | Ricorsivo: {ricorsivo} | Nascosti: {includi_nascosti}")
    logging.info(f"Include patterns: {include_pats or '---'}")
    logging.info(f"Exclude patterns: {exclude_pats or '---'}")

    old_attrs = _abilita_modalità_raw()
    snapshot_vecchio = scansiona_directory(paths, ricorsivo, includi_nascosti,
                                           include_pats, exclude_pats)
    try:
        while True:
            pronto, _, _ = select.select([sys.stdin], [], [], intervallo)
            if pronto:
                ch = sys.stdin.read(1)
                if ch == '\x1b':  # ESC
                    logging.info("ESC premuto: ritorno al menu.")
                    break

            snapshot_nuovo = scansiona_directory(paths, ricorsivo, includi_nascosti,
                                                 include_pats, exclude_pats)
            aggiunti, rimossi, modificati = confronta_snapshot(snapshot_vecchio, snapshot_nuovo)

            for k in sorted(aggiunti):
                base, rel = k.split("|", 1)
                tipo = "DIR" if rel.endswith("/") else "FILE"
                logging.info(f"[{base}] +Aggiunto   {tipo}: {rel.rstrip('/')}")
            for k in sorted(rimossi):
                base, rel = k.split("|", 1)
                tipo = "DIR" if rel.endswith("/") else "FILE"
                logging.info(f"[{base}] -Rimosso   {tipo}: {rel.rstrip('/')}")
            for k in sorted(modificati):
                base, rel = k.split("|", 1)
                tipo = "DIR" if rel.endswith("/") else "FILE"
                logging.info(f"[{base}] *Modificato {tipo}: {rel.rstrip('/')}")

            snapshot_vecchio = snapshot_nuovo

    finally:
        _ripristina_modalità(old_attrs)
        logging.info("==== Monitor arrestato ====")

def main():
    """
    Ciclo principale: mostra menu e avvia il monitor finché non si esce.
    """
    while True:
        params = menu()
        ciclo_monitoring(*params)

if __name__ == "__main__":
    main()
