from pathlib import Path
import os
from cryptography.fernet import Fernet

def load_encrypted_env():
    key = os.getenv("DOTENV_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("DOTENV_ENCRYPTION_KEY env var not set")

    root = Path(__file__).resolve().parent
    enc_file = root / ".env.encrypted"
    if not enc_file.exists():
        raise FileNotFoundError(f"No encrypted env at {enc_file}")

    fernet = Fernet(key.encode())
    decrypted = fernet.decrypt(enc_file.read_bytes()).decode()

    for line in decrypted.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
