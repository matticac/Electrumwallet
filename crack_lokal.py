import hashlib
import time
import multiprocessing
from datetime import datetime

# Wir laden die Electrum-Funktionen
from electrum.mnemonic import Mnemonic, is_new_seed
from electrum import version

# --- KONFIGURATION ---
FIXED_YEAR = 2026
FIXED_MONTH = 1
FIXED_DAY = 13       # Prüfe, ob das Datum in der VM stimmt!

TARGET_HOUR = 10
TARGET_MINUTE = 42

# Wir suchen riesig (4 Stunden), aber lassen uns ALLE Ergebnisse zeigen
SEARCH_RADIUS_MINUTES = 60
# ---------------------

def worker_hack(start_ts, end_ts, target_word, result_queue):
    mnemo = Mnemonic('en')
    
    # Wir laufen den ganzen Bereich durch, ohne abzubrechen
    for ts in range(start_ts, end_ts + 1):
        
        # --- DER HACK ---
        t_str = str(ts)
        h = hashlib.sha256(t_str.encode('utf-8')).hexdigest()
        entropy = int(h, 16)
        
        # Seed generieren
        nonce = 0
        while True:
            nonce += 1
            i = entropy + nonce
            seed = mnemo.mnemonic_encode(i)
            if is_new_seed(seed, version.SEED_PREFIX_SW):
                break
        
        # Prüfung: Beginnt der Seed mit dem Wort?
        if seed.startswith(target_word):
            # TREFFER! Wir schicken ihn an den Hauptprozess
            result_queue.put((ts, seed))

    # WICHTIG: Wenn der Kern fertig ist, sendet er ein "Signal" (None)
    result_queue.put(None)

def main():
    # 1. Zielzeit berechnen
    target_dt = datetime(FIXED_YEAR, FIXED_MONTH, FIXED_DAY, TARGET_HOUR, TARGET_MINUTE, 0)
    center_ts = int(target_dt.timestamp())
    
    # 2. Start/Ende berechnen
    total_seconds = SEARCH_RADIUS_MINUTES * 60
    global_start = center_ts - total_seconds
    global_end = center_ts + total_seconds
    total_range = global_end - global_start

    print(f"--- MULTICORE: SUCHE ALLE TREFFER ---")
    print(f"Zeitraum: {datetime.fromtimestamp(global_start)} bis {datetime.fromtimestamp(global_end)}")
    
    target_word = input("Gib das ERSTE Wort ein (z.B. armed): ").strip().lower()
    
    cpu_count = multiprocessing.cpu_count()
    print(f"\nStarte Suche auf {cpu_count} Kernen... (Bitte warten)")
    print("-" * 60)

    # 3. Arbeit verteilen
    chunk_size = total_range // cpu_count
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(cpu_count):
        p_start = global_start + (i * chunk_size)
        p_end = global_start + ((i + 1) * chunk_size) if i < cpu_count - 1 else global_end
        
        # Wir übergeben diesmal kein "Event" zum Stoppen
        p = multiprocessing.Process(target=worker_hack, args=(p_start, p_end, target_word, result_queue))
        processes.append(p)
        p.start()

    # 4. Ergebnisse einsammeln
    finished_workers = 0
    found_any = False

    # Solange noch nicht alle Kerne "Fertig" (None) gemeldet haben...
    while finished_workers < cpu_count:
        item = result_queue.get() # Wartet auf Daten
        
        if item is None:
            # Ein Kern ist fertig
            finished_workers += 1
        else:
            # Ein Treffer!
            ts, seed = item
            readable_time = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            
            # Ist es nah an unserer Zielzeit?
            marker = ""
            if abs(ts - center_ts) < 300: # Wenn innerhalb von 5 Min um 10:30
                marker = " <--- HEISSER KANDIDAT (10:30)"
            
            print(f"[{readable_time}] {seed}{marker}")
            found_any = True

    print("-" * 60)
    if not found_any:
        print("Keine Treffer gefunden.")
    else:
        print("Suche beendet. Alle möglichen Seeds oben aufgelistet.")
    
    # Aufräumen
    for p in processes:
        p.join()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
    input("\nDrücke Enter zum Beenden...")