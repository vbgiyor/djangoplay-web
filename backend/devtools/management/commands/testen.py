from cryptography.fernet import Fernet, InvalidToken

key = b'P5jzxZIM1JCcpzi6qXqjJkbYlsepKu3rNxcqG8KnkGY='
encrypted_value = 'gAAAAABovtnzbi8p3qH9tvAfI9zdSwaVLMv8ardMKooWQT1BMrZ0bHHxQ6wabSkrdLCBLD-cucjzSxyBXq90xDoVkWwSqqpMdg=='

fernet = Fernet(key)
try:
    decrypted = fernet.decrypt(encrypted_value.encode('utf-8'))
    print(f"Decrypted value: {decrypted.decode('utf-8')}")
except InvalidToken:
    print("Failed to decrypt: Invalid encryption key or corrupted data.")
