# Bitcoin Mnemonic TX Checker

Generate random BIP39 mnemonics, derive BIP84 Bitcoin addresses, and check whether the derived addresses have transaction history by querying multiple public Bitcoin API endpoints.

## Features

- Random BIP39 mnemonic generation
- Native SegWit Bitcoin address derivation via BIP84
- Support for multiple accounts and addresses
- Rotation across 3 public API endpoints:
  - Blockstream
  - Mempool.space
  - Blockchain.info
- Exponential backoff for HTTP 429 responses
- Fixed delay between requests
- TXT output with matching results only
- Per-endpoint request counter

## Requirements

- Python 3.10 or newer recommended
- Internet connection
- Python packages listed in `requirements.txt`

## Installation

Clone the repository or download the files, then install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

All customizable parameters are located at the top of the script inside the `Configuration` section.

Example:

```python
MNEMONIC_BITS = 256
NUM_ADDRESSES = 1
NUM_ACCOUNTS = 1
NUM_MNEMONICS = 1000

FIXED_DELAY_SECONDS = 1
MAX_BACKOFF_SECONDS = 30
REQUEST_TIMEOUT = 15

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILENAME_PREFIX = "balance"
```

### Output folder

By default, the script saves results in an `output` folder located inside the project directory.

```python
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
```

If needed, this can be replaced with a custom absolute path.

## Usage

Run the script with:

```bash
python mnemonic_tx_checker.py
```

The script will:

1. Generate a random BIP39 mnemonic
2. Derive BIP84 external Bitcoin addresses
3. Query the configured public APIs
4. Check whether each address has transaction history
5. Save matching results to a timestamped `.txt` file

## Output

The script creates a text file in the output directory, for example:

```bash
output/balance_YYYYMMDD_HHMMSS.txt
```

The file includes, for matching addresses only:

- Mnemonic
- Account index
- Derivation path
- Address
- Private key (WIF)
- Balance

## Dependencies

Install these packages:

```txt
requests
mnemonic
bip-utils
```

## Security warning

This script writes sensitive data such as mnemonics and private keys to the output file.

- Do not upload generated output files to GitHub
- Do not share generated mnemonics or private keys
- Do not use this script with wallets containing real funds unless you fully understand the risks

## Disclaimer

This project is provided for educational and experimental purposes only. Use it responsibly and at your own risk.
