# -*- coding: utf-8 -*-
"""
Generate random BIP39 mnemonics, derive BIP84 Bitcoin addresses, and check
whether each derived address has transaction history using multiple public APIs.

Features:
- Random BIP39 mnemonic generation
- BIP84 derivation for multiple accounts and addresses
- Rotation across 3 public API endpoints
- Exponential backoff on HTTP 429 responses
- Fixed delay after successful requests
- TXT output for matching addresses only
- Final per-endpoint request counter
"""

import itertools
import time
from datetime import datetime
from pathlib import Path

import requests
from mnemonic import Mnemonic
from bip_utils import Bip39SeedGenerator, Bip84, Bip84Coins, Bip44Changes


# ============================================================
# Configuration
# Edit these values to customize the script behavior
# ============================================================

MNEMONIC_BITS = 256               # 128 = 12 words, 256 = 24 words
NUM_ADDRESSES = 1                 # Number of external addresses per account
NUM_ACCOUNTS = 1                  # Number of accounts to scan
NUM_MNEMONICS = 10              # Number of mnemonics to generate

FIXED_DELAY_SECONDS = 1           # Delay after each successful request
MAX_BACKOFF_SECONDS = 30          # Maximum backoff on HTTP 429
REQUEST_TIMEOUT = 15              # Timeout for HTTP requests in seconds

# Output folder options:
# Option 1: relative folder inside the project directory
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

# Option 2: custom absolute folder (uncomment and edit if needed)
# OUTPUT_DIR = Path(r"/home/your_user/your_custom_folder")

OUTPUT_FILENAME_PREFIX = "balance"


# ============================================================
# API endpoints
# ============================================================

API_ENDPOINTS = [
    "https://blockstream.info/api/address/",
    "https://mempool.space/api/address/",
    "https://blockchain.info/rawaddr/",
]


# ============================================================
# Global runtime objects
# ============================================================

endpoint_cycle = itertools.cycle(API_ENDPOINTS)
request_counter = {endpoint: 0 for endpoint in API_ENDPOINTS}


def get_address_data(address):
    """
    Query the available endpoints in rotation and return funded/spent data.

    Returns:
        dict: {"funded": int, "spent": int}
        None: if all endpoints fail
    """
    global endpoint_cycle

    backoff_time = 1

    for _ in range(len(API_ENDPOINTS)):
        base_url = next(endpoint_cycle)
        url = base_url + address

        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            request_counter[base_url] += 1

            if response.status_code == 200:
                time.sleep(FIXED_DELAY_SECONDS)
                data = response.json()

                if "blockstream" in base_url:
                    return {
                        "funded": data["chain_stats"]["funded_txo_sum"],
                        "spent": data["chain_stats"]["spent_txo_sum"],
                    }

                elif "mempool.space" in base_url:
                    return {
                        "funded": data.get("chain_stats", {}).get("funded_txo_sum", 0),
                        "spent": data.get("chain_stats", {}).get("spent_txo_sum", 0),
                    }

                elif "blockchain.info" in base_url:
                    return {
                        "funded": data.get("total_received", 0),
                        "spent": data.get("total_sent", 0),
                    }

            elif response.status_code == 429:
                print(
                    f"429 Too Many Requests on {base_url} - "
                    f"waiting {backoff_time} seconds before trying another endpoint..."
                )
                time.sleep(backoff_time)
                backoff_time = min(backoff_time * 2, MAX_BACKOFF_SECONDS)
                continue

            else:
                print(f"HTTP error {response.status_code} on {base_url}")
                continue

        except Exception as exc:
            print(f"Request error on {base_url}: {exc}")
            continue

    return None


def format_elapsed_time(seconds_total):
    """
    Convert elapsed seconds to hours, minutes, seconds.
    """
    hours = int(seconds_total // 3600)
    minutes = int((seconds_total % 3600) // 60)
    seconds = int(seconds_total % 60)
    return hours, minutes, seconds


def main():
    """
    Main script execution.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"{OUTPUT_FILENAME_PREFIX}_{timestamp}.txt"

    start_total = time.time()
    any_positive_global = False

    with open(output_file, "w", encoding="utf-8") as out:
        out.write("Bitcoin scan results (addresses with transaction history)\n")
        out.write(f"Generated mnemonics: {NUM_MNEMONICS}\n")
        out.write("=" * 60 + "\n\n")

        for mnemo_round in range(NUM_MNEMONICS):
            start_round = time.time()

            mnemo = Mnemonic("english")
            mnemonic = mnemo.generate(MNEMONIC_BITS)

            print("\n" + "=" * 60)
            print(f"[{mnemo_round + 1}/{NUM_MNEMONICS}] New mnemonic generated:")
            print(mnemonic)
            print("=" * 60)

            seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
            bip84_ctx = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)

            found_positive = False

            for account_idx in range(NUM_ACCOUNTS):
                print(f"\n=== Checking account m/84'/0'/{account_idx}' ===")

                account_ctx = (
                    bip84_ctx.Purpose()
                    .Coin()
                    .Account(account_idx)
                    .Change(Bip44Changes.CHAIN_EXT)
                )

                for addr_idx in range(NUM_ADDRESSES):
                    addr_ctx = account_ctx.AddressIndex(addr_idx)
                    address = addr_ctx.PublicKey().ToAddress()
                    privkey = addr_ctx.PrivateKey().ToWif()

                    result = get_address_data(address)

                    if result is not None:
                        funded = result["funded"]
                        spent = result["spent"]
                        balance_sat = funded - spent

                        if funded > 0 or spent > 0:
                            balance_btc = balance_sat / 100_000_000
                            derivation_path = f"m/84'/0'/{account_idx}'/0/{addr_idx}"

                            out.write(f"\n--- MNEMONIC {mnemo_round + 1}/{NUM_MNEMONICS} ---\n")
                            out.write(f"Mnemonic: {mnemonic}\n")
                            out.write(f"Account: {account_idx}\n")
                            out.write(f"Derivation Path: {derivation_path}\n")
                            out.write(f"Address: {address}\n")
                            out.write(f"PrivKey: {privkey}\n")
                            out.write(f"Balance: {balance_btc} BTC\n")
                            out.write("-" * 40 + "\n")

                            print(
                                f"[Account {account_idx}] Address: {address} "
                                f"- Balance: {balance_btc:.8f} BTC ✅"
                            )

                            found_positive = True
                            any_positive_global = True
                        else:
                            print(
                                f"[Account {account_idx}] Address: {address} "
                                f"- No transaction history"
                            )
                    else:
                        print(
                            f"Unable to retrieve data for address {address} "
                            f"from all endpoints."
                        )

            elapsed_round = time.time() - start_round
            hours, minutes, seconds = format_elapsed_time(elapsed_round)

            print(f"\nExecution time for this mnemonic: {hours}h {minutes}m {seconds}s")

            if not found_positive:
                print("--- NO TRANSACTION HISTORY FOUND FOR THIS MNEMONIC ---")

    elapsed_total = time.time() - start_total
    hours, minutes, seconds = format_elapsed_time(elapsed_total)

    print(f"\n>>> COMPLETED: {NUM_MNEMONICS} mnemonics checked.")
    print(f"Total duration: {hours}h {minutes}m {seconds}s")
    print(f"Results saved in: {output_file}")

    print("\nRequests made per endpoint:")
    for endpoint, count in request_counter.items():
        print(f"{endpoint}: {count} requests")

    if not any_positive_global:
        print("\n" + "=" * 60)
        print("       NO MNEMONIC WITH TRANSACTION HISTORY FOUND")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()