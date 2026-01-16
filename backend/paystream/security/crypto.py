from cryptography.fernet import Fernet, InvalidToken


def generate_encryption_key() -> bytes:
    """Generate a new encryption key (run once and store securely)."""
    return Fernet.generate_key()

def encrypt_value(value: str, key: bytes) -> str:
    """Encrypt a value using the provided key."""
    fernet = Fernet(key)
    encrypted = fernet.encrypt(value.encode('utf-8'))
    return encrypted.decode('utf-8')

def decrypt_value(encrypted: str, key: bytes) -> str:
    """Decrypt an encrypted value using the provided key. Raises error if invalid."""
    fernet = Fernet(key)
    try:
        decrypted = fernet.decrypt(encrypted.encode('utf-8'))
        return decrypted.decode('utf-8')
    except InvalidToken:
        raise ValueError("Invalid encryption key or corrupted data.")

# Example usage in a Django service/script:
# key = generate_encryption_key()  # b'...' (store this securely, e.g., in os.environ['ENCRYPTION_KEY'])
# encrypted_password = encrypt_value("paperboat", key)
# print(encrypted_password)  # Something like 'gAAAAAB...'

# Later, to use:
# original_password = decrypt_value(encrypted_password, key)
# # Now use original_password to create superuser, e.g., User.objects.create_superuser(username=..., email=..., password=original_password)
