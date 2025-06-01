# encrypted_env_loader.py
from pathlib import Path
import os
from cryptography.fernet import Fernet # Assuming you're using Fernet

# --- Configuration for the encrypted file path ---
# Define the default filename
DEFAULT_ENCRYPTED_FILENAME = ".env.encrypted.bak"

# Define the default location for the encrypted file relative to this script's directory.
# If this script (encrypted_env_loader.py) is in your project root (e.g., /joel/calendar_bot/),
# and your secrets file is in /joel/calendar_bot/secrets/.env.encrypted.bak
DEFAULT_PATH_TO_ENCRYPTED_FILE = Path(__file__).resolve().parent / "secrets" / DEFAULT_ENCRYPTED_FILENAME

# Get the actual path from an environment variable if set, otherwise use the default.
# This ENCRYPTED_ENV_FILE_PATH will be set in your docker-compose.yml later,
# or you could set it in your shell for local testing if you deviate from the default.
ENCRYPTED_FILE_TO_LOAD = Path(os.getenv("ENCRYPTED_ENV_FILE_PATH", str(DEFAULT_PATH_TO_ENCRYPTED_FILE)))


def load_encrypted_env():
    """
    Loads and decrypts the .env.encrypted.bak file, then sets the
    decrypted key-value pairs as environment variables.
    
    The path to the encrypted file is determined by the
    ENCRYPTED_ENV_FILE_PATH environment variable. If not set,
    it defaults to 'secrets/.env.encrypted.bak' relative to this script's location.
    
    The DOTENV_ENCRYPTION_KEY environment variable must be set for decryption.
    """
    key_str = os.getenv("DOTENV_ENCRYPTION_KEY")
    if not key_str:
        raise RuntimeError("DOTENV_ENCRYPTION_KEY environment variable not set. This key is required for decryption.")

    if not ENCRYPTED_FILE_TO_LOAD.exists():
        # Log this or print it for better debugging if running directly
        print(f"Attempted to find encrypted file at: {ENCRYPTED_FILE_TO_LOAD}")
        print(f"Based on ENCRYPTED_ENV_FILE_PATH env var (if set) or default: {DEFAULT_PATH_TO_ENCRYPTED_FILE}")
        raise FileNotFoundError(f"Encrypted environment file not found at {ENCRYPTED_FILE_TO_LOAD}")

    try:
        key_bytes = key_str.encode() # Key must be bytes
        fernet = Fernet(key_bytes)
        
        encrypted_data = ENCRYPTED_FILE_TO_LOAD.read_bytes()
        decrypted_data = fernet.decrypt(encrypted_data).decode()

        for line in decrypted_data.splitlines():
            line = line.strip()
            # Ignore comments and empty lines
            if line and not line.startswith("#") and "=" in line:
                # Split only on the first equals sign
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                # Remove surrounding quotes from value if present (optional, but common in .env files)
                if v.startswith('"') and v.endswith('"'):
                    v = v[1:-1]
                elif v.startswith("'") and v.endswith("'"):
                    v = v[1:-1]
                
                os.environ.setdefault(k, v) # setdefault won't overwrite existing env vars
        
        # Optional: Log that environment variables have been loaded
        # (You'd need to import your logger or use print for this script)
        # print("Successfully loaded and decrypted environment variables.")

    except FileNotFoundError: # Already handled above, but good for clarity
        raise
    except ImportError:
        raise ImportError("Cryptography library (Fernet) is not installed. Please install it: pip install cryptography")
    except Exception as e:
        # Catch other potential errors during decryption or parsing
        raise RuntimeError(f"Failed to load or decrypt environment file '{ENCRYPTED_FILE_TO_LOAD}': {e}")

# Example of how app.py would use it (no change needed in app.py):
# from encrypted_env_loader import load_encrypted_env
# load_encrypted_env() # This will now use the flexible path logic