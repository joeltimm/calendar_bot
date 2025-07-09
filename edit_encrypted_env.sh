#!/bin/bash
# ~/calendar_bot/edit_encrypted_env.sh
#
# Decrypts the encrypted .env file, opens it for editing,
# then re-encrypts it and deletes the plaintext temporary file.
#
# IMPORTANT: DOTENV_ENCRYPTION_KEY must be set in your shell environment
#            before running this script.
# Usage: source ./edit_encrypted_env.sh (or just ./edit_encrypted_env.sh if executable)

# --- Configuration ---
ENCRYPTED_FILE="/home/joel/my_super_secure_secrets/.env.encrypted.bak"
TEMP_PLAINTEXT_FILE="./.env.temp_edit" # Temporary plaintext file in project root

# --- Check for encryption key ---
if [ -z "$DOTENV_ENCRYPTION_KEY" ]; then
  echo "ERROR: DOTENV_ENCRYPTION_KEY is not set in your environment."
  echo "Please run: export DOTENV_ENCRYPTION_KEY=\"your_key_here\""
  exit 1
fi

# --- Decrypt ---
echo "Decrypting $ENCRYPTED_FILE to $TEMP_PLAINTEXT_FILE for editing..."
python3 decrypt_env.py "$ENCRYPTED_FILE" > "$TEMP_PLAINTEXT_FILE"
if [ $? -ne 0 ]; then
  echo "ERROR: Decryption failed. Aborting."
  rm -f "$TEMP_PLAINTEXT_FILE" # Clean up temp file on failure
  exit 1
fi

# --- Open for editing ---
echo "Opening $TEMP_PLAINTEXT_FILE for editing. Save and close the editor when done."
# Use your preferred editor (nano, vim, code, etc.)
# 'code --wait' for VS Code, 'vim' or 'nano' for terminal editors
nano "$TEMP_PLAINTEXT_FILE"

# --- Encrypt back ---
echo "Encrypting changes from $TEMP_PLAINTEXT_FILE back to $ENCRYPTED_FILE..."
# encrypt_env.py expects .env in the current directory, so we temporarily move it
mv "$TEMP_PLAINTEXT_FILE" ./.env
python3 encrypt_env.py
if [ $? -ne 0 ]; then
  echo "ERROR: Re-encryption failed. The plaintext file is still at ./.env."
  echo "Please manually inspect and delete it after resolving the issue."
  exit 1
fi

# --- Clean up plaintext file ---
echo "Deleting temporary plaintext file ./.env"
rm ./.env

# --- Move encrypted file to secure location ---
echo "Moving newly encrypted file to secure location: $ENCRYPTED_FILE"
mv ./secrets/.env.encrypted.bak "$ENCRYPTED_FILE"

echo "Encryption process complete. Remember to restart your Docker services if changes were made."
