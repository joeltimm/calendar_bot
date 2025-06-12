# decrypt_env.py
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken

def decrypt_and_print_env():
    """
    Finds, decrypts, and prints the contents of the encrypted .env file.
    Requires DOTENV_ENCRYPTION_KEY to be set in the environment.
    """
    # Get the decryption key from environment variables
    key_str = os.getenv("DOTENV_ENCRYPTION_KEY")
    if not key_str:
        raise RuntimeError("CRITICAL: DOTENV_ENCRYPTION_KEY environment variable not set.")

    # Define the path to the encrypted file
    encrypted_file_path = Path(__file__).resolve().parent / "secrets" / ".env.encrypted.bak"

    if not encrypted_file_path.exists():
        raise FileNotFoundError(f"Encrypted environment file not found at: {encrypted_file_path}")

    print(f"--> Found encrypted file at: {encrypted_file_path}")

    try:
        fernet = Fernet(key_str.encode())

        # Read the encrypted bytes from the file
        encrypted_data = encrypted_file_path.read_bytes()

        # Decrypt the data
        decrypted_data = fernet.decrypt(encrypted_data).decode()

        # Print the decrypted content for you to copy
        print("\n--- Decrypted .env Content (copy this, edit, and save as .env) ---")
        print("------------------------------------------------------------------")
        print(decrypted_data)
        print("------------------------------------------------------------------")

    except InvalidToken:
        print("\n❌ DECRYPTION FAILED: The DOTENV_ENCRYPTION_KEY is incorrect or the encrypted file is corrupted.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred during decryption: {e}")

if __name__ == "__main__":
    decrypt_and_print_env()
