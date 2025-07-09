# ~/calendar_bot/decrypt_env.py (CORRECTED to accept command-line argument)

import os
from pathlib import Path
from cryptography.fernet import Fernet
import sys # ADD THIS IMPORT

def decrypt_and_print_env():
    """
    Decrypts the encrypted environment file and prints its content.
    Expects DOTENV_ENCRYPTION_KEY to be set in the environment.
    Accepts the path to the encrypted file as a command-line argument.
    """
    key_str = os.getenv("DOTENV_ENCRYPTION_KEY")
    if not key_str:
        # Changed to print to stderr and exit with error code, better for scripting
        print("CRITICAL: DOTENV_ENCRYPTION_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        # Changed to print to stderr and exit with error code
        print("Usage: python3 decrypt_env.py <path_to_encrypted_file>", file=sys.stderr)
        sys.exit(1)

    # Get the encrypted file path from the command-line argument
    # .resolve() makes it an absolute path
    encrypted_file_path = Path(sys.argv[1]).resolve()

    if not encrypted_file_path.exists():
        print(f"FileNotFoundError: Encrypted environment file not found at: {encrypted_file_path}", file=sys.stderr)
        sys.exit(1)

    print(f"--> Reading encrypted data from: {encrypted_file_path}", file=sys.stderr) # Log to stderr

    try:
        fernet = Fernet(key_str.encode())

        with open(encrypted_file_path, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = fernet.decrypt(encrypted_data)

        # Print decrypted data to stdout, which can be redirected
        sys.stdout.buffer.write(decrypted_data) # Use sys.stdout.buffer.write for bytes

    except Exception as e:
        print(f"\n❌ An error occurred during decryption: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    decrypt_and_print_env()
