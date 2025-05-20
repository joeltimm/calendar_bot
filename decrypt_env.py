import os
from cryptography.fernet import Fernet

key = os.getenv("DOTENV_ENCRYPTION_KEY")
if not key:
    raise RuntimeError("DOTENV_ENCRYPTION_KEY env var not set")

fernet = Fernet(key.encode())

with open(".env.encrypted", "rb") as f:
    enc = f.read()

data = fernet.decrypt(enc)
with open(".env", "wb") as f:
    f.write(data)

print("✅ .env decrypted from .env.encrypted")
