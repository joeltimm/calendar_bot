#!/bin/bash
# ~/calendar_bot/load_runtime_env.sh
#
# Decrypts the encrypted .env file, loads variables into the current shell environment,
# and then immediately deletes the temporary plaintext file.
#
# IMPORTANT: DOTENV_ENCRYPTION_KEY must be set in your shell environment
#            before sourcing this script.
# Usage: source ./load_runtime_env.sh (or just . ./load_runtime_env.sh)

# --- Configuration ---
ENCRYPTED_FILE="/home/joel/my_super_secure_secrets/.env.encrypted.bak"
TEMP_PLAINTEXT_FILE="./.env.temp_load" # Temporary plaintext file in project root

# --- Check for encryption key ---
if [ -z "$DOTENV_ENCRYPTION_KEY" ]; then
  echo "ERROR: DOTENV_ENCRYPTION_KEY is not set in your environment."
  echo "Please run: export DOTENV_ENCRYPTION_KEY=\"your_key_here\""
  exit 1
fi

# --- Decrypt to temporary file ---
python3 decrypt_env.py "$ENCRYPTED_FILE" > "$TEMP_PLAINTEXT_FILE"
if [ $? -ne 0 ]; then
  echo "ERROR: Decryption failed. Aborting."
  rm -f "$TEMP_PLAINTEXT_FILE" # Clean up temp file on failure
  exit 1
fi

# --- Load variables into current shell ---
# The 'set -a' exports all subsequent variables.
# The 'set +a' turns it off.
# This ensures all variables from the decrypted file are exported.
set -a
source "$TEMP_PLAINTEXT_FILE"
set +a

# --- Clean up temporary plaintext file ---
rm "$TEMP_PLAINTEXT_FILE"
if [ $? -ne 0 ]; then
  echo "WARNING: Failed to delete temporary plaintext file: $TEMP_PLAINTEXT_FILE"
fi

echo "✅ Environment variables loaded into current shell session."
