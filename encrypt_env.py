#encrypt_env.py
# ~/calendar_bot/encrypt_env.py (Corrected Version)

import os
from pathlib import Path
from cryptography.fernet import Fernet

def encrypt_env_file():

#    Finds .env, encrypts it, and saves it to the correct location
#    (secrets/.env.encrypted.bak) for the application to use.
#    Requires DOTENV_ENCRYPTION_KEY to be set in the environment.

    key_str = os.getenv("DOTENV_ENCRYPTION_KEY")
    if not key_str:
        raise RuntimeError("CRITICAL: DOTENV_ENCRYPTION_KEY environment variable not set.")

    # Define paths relative to this script's location
    project_root = Path(__file__).resolve().parent
    source_env_file = project_root / ".env"
    secrets_dir = project_root / "secrets"
    encrypted_file_path = secrets_dir / ".env.encrypted.bak" # Correct destination path

    # Ensure the source .env file exists
    if not source_env_file.exists():
        raise FileNotFoundError(f"Source file not found at: {source_env_file}\nPlease create your .env file.")

    # Ensure the secrets/ directory exists
    secrets_dir.mkdir(parents=True, exist_ok=True)

    print(f"--> Reading plain text from: {source_env_file}")
    print(f"--> Encrypting and saving to: {encrypted_file_path}")

    try:
        fernet = Fernet(key_str.encode())
        
        # Read the source data
        with open(source_env_file, "rb") as f:
            data = f.read()

        # Encrypt the data
        encrypted_data = fernet.encrypt(data)
        
        # Write the encrypted data to the correct destination file
        with open(encrypted_file_path, "wb") as f:
            f.write(encrypted_data)

        print(f"\n✅ Successfully encrypted '{source_env_file.name}' to '{encrypted_file_path}'")

    except Exception as e:
        print(f"\n❌ An error occurred during encryption: {e}")

if __name__ == "__main__":
    encrypt_env_file()
