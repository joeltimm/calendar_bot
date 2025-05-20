import os
from cryptography.fernet import Fernet

key = os.getenv("DOTENV_ENCRYPTION_KEY")
if not key:
    raise RuntimeError("DOTENV_ENCRYPTION_KEY env var not set")

fernet = Fernet(key.encode())

with open(".env", "rb") as f:
    data = f.read()

enc = fernet.encrypt(data)
with open(".env.encrypted", "wb") as f:
    f.write(enc)

print("✅ .env encrypted → .env.encrypted")
