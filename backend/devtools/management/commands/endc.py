from pathlib import Path

import environ
from django.core.management.base import BaseCommand
from paystream.security.crypto import decrypt_value, encrypt_value


class Command(BaseCommand):
    help = 'Encrypt or decrypt a specific environment variable key.'

    def add_arguments(self, parser):
        parser.add_argument('--key', type=str, required=True, help='Environment variable key to encrypt/decrypt')
        parser.add_argument('--decrypt', action='store_true', help='Decrypt the key instead of encrypting')

    def handle(self, *args, **options):
        env = environ.Env()
        env_path = Path(__file__).resolve().parent.parent / '.env'
        environ.Env.read_env(env_path, override=True)

        encryption_key = env('ENCRYPTION_KEY')
        if not encryption_key:
            self.stderr.write(self.style.ERROR('ENCRYPTION_KEY must be set in .env'))
            return
        key_bytes = encryption_key.encode('utf-8')

        target_key = options['key']
        value = env(target_key, default=None)
        if not value:
            self.stderr.write(self.style.ERROR(f'{target_key} not found in .env'))
            return

        try:
            if options['decrypt']:
                result = decrypt_value(value, key_bytes)
                self.stdout.write(self.style.SUCCESS(f'Decrypted {target_key}: {result}'))
            else:
                result = encrypt_value(value, key_bytes)
                self.stdout.write(self.style.SUCCESS(f'Encrypted {target_key}: {result}'))
                # Update .env file
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                with open(env_path, 'w') as f:
                    for line in lines:
                        if line.startswith(f'{target_key}='):
                            f.write(f'{target_key}={result}\n')
                        else:
                            f.write(line)
                self.stdout.write(self.style.SUCCESS(f'Updated {env_path} with new {target_key} value.'))
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
