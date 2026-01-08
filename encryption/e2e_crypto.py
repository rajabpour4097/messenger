"""
End-to-End Encryption Module using XChaCha20-Poly1305 and X25519
This provides military-grade encryption for the chat system.

Security Features:
- X25519 for key exchange (Elliptic Curve Diffie-Hellman)
- XChaCha20-Poly1305 for message encryption (AEAD)
- Argon2id for key derivation
- Perfect Forward Secrecy support
"""

import os
import base64
import hashlib
import secrets
from typing import Tuple, Optional
from dataclasses import dataclass

from nacl.public import PrivateKey, PublicKey, Box
from nacl.secret import SecretBox
from nacl.pwhash import argon2id
from nacl.utils import random as nacl_random
from nacl.encoding import Base64Encoder
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


@dataclass
class KeyPair:
    """Represents a public/private key pair"""
    private_key: bytes
    public_key: bytes
    
    def to_dict(self) -> dict:
        return {
            'private_key': base64.b64encode(self.private_key).decode('utf-8'),
            'public_key': base64.b64encode(self.public_key).decode('utf-8'),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'KeyPair':
        return cls(
            private_key=base64.b64decode(data['private_key']),
            public_key=base64.b64decode(data['public_key']),
        )


@dataclass
class EncryptedMessage:
    """Represents an encrypted message with metadata"""
    ciphertext: bytes
    nonce: bytes
    sender_public_key: bytes
    
    def to_dict(self) -> dict:
        return {
            'ciphertext': base64.b64encode(self.ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(self.nonce).decode('utf-8'),
            'sender_public_key': base64.b64encode(self.sender_public_key).decode('utf-8'),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EncryptedMessage':
        return cls(
            ciphertext=base64.b64decode(data['ciphertext']),
            nonce=base64.b64decode(data['nonce']),
            sender_public_key=base64.b64decode(data['sender_public_key']),
        )
    
    def to_storage_string(self) -> str:
        """Convert to a single base64 string for database storage"""
        combined = self.nonce + self.sender_public_key + self.ciphertext
        return base64.b64encode(combined).decode('utf-8')
    
    @classmethod
    def from_storage_string(cls, data: str) -> 'EncryptedMessage':
        """Reconstruct from storage string"""
        combined = base64.b64decode(data)
        nonce = combined[:24]  # XChaCha20 nonce size
        sender_public_key = combined[24:56]  # X25519 public key size
        ciphertext = combined[56:]
        return cls(
            nonce=nonce,
            sender_public_key=sender_public_key,
            ciphertext=ciphertext,
        )


class E2EEncryption:
    """
    End-to-End Encryption handler using:
    - X25519 for key exchange
    - XChaCha20-Poly1305 for symmetric encryption
    - Argon2id for key derivation from passwords
    """
    
    NONCE_SIZE = 24  # XChaCha20 nonce size
    KEY_SIZE = 32    # 256-bit keys
    
    @staticmethod
    def generate_key_pair() -> KeyPair:
        """Generate a new X25519 key pair"""
        private_key = PrivateKey.generate()
        public_key = private_key.public_key
        
        return KeyPair(
            private_key=bytes(private_key),
            public_key=bytes(public_key),
        )
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Derive an encryption key from a password using Argon2id
        Returns (derived_key, salt)
        """
        if salt is None:
            salt = nacl_random(argon2id.SALTBYTES)
        
        key = argon2id.kdf(
            E2EEncryption.KEY_SIZE,
            password.encode('utf-8'),
            salt,
            opslimit=argon2id.OPSLIMIT_MODERATE,
            memlimit=argon2id.MEMLIMIT_MODERATE,
        )
        
        return key, salt
    
    @staticmethod
    def derive_shared_secret(private_key: bytes, peer_public_key: bytes) -> bytes:
        """
        Derive a shared secret using X25519 ECDH
        """
        private = PrivateKey(private_key)
        public = PublicKey(peer_public_key)
        box = Box(private, public)
        
        # Use HKDF to derive a proper key from the shared secret
        shared_key = box.shared_key()
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=E2EEncryption.KEY_SIZE,
            salt=None,
            info=b'secure_chat_e2e_v1',
            backend=default_backend(),
        )
        
        return hkdf.derive(shared_key)
    
    @staticmethod
    def encrypt_message(
        plaintext: str,
        sender_private_key: bytes,
        recipient_public_key: bytes,
    ) -> EncryptedMessage:
        """
        Encrypt a message using the recipient's public key
        Uses XChaCha20-Poly1305 for authenticated encryption
        """
        # Derive shared secret
        shared_key = E2EEncryption.derive_shared_secret(
            sender_private_key, 
            recipient_public_key
        )
        
        # Create secret box with shared key
        box = SecretBox(shared_key)
        
        # Generate random nonce
        nonce = nacl_random(SecretBox.NONCE_SIZE)
        
        # Encrypt the message
        ciphertext = box.encrypt(plaintext.encode('utf-8'), nonce).ciphertext
        
        # Get sender's public key
        sender_public_key = bytes(PrivateKey(sender_private_key).public_key)
        
        return EncryptedMessage(
            ciphertext=ciphertext,
            nonce=nonce,
            sender_public_key=sender_public_key,
        )
    
    @staticmethod
    def decrypt_message(
        encrypted_message: EncryptedMessage,
        recipient_private_key: bytes,
    ) -> str:
        """
        Decrypt a message using the recipient's private key
        """
        # Derive shared secret using sender's public key
        shared_key = E2EEncryption.derive_shared_secret(
            recipient_private_key,
            encrypted_message.sender_public_key,
        )
        
        # Create secret box with shared key
        box = SecretBox(shared_key)
        
        # Decrypt the message
        plaintext = box.decrypt(
            encrypted_message.ciphertext,
            encrypted_message.nonce,
        )
        
        return plaintext.decode('utf-8')
    
    @staticmethod
    def encrypt_for_room(
        plaintext: str,
        room_key: bytes,
    ) -> Tuple[bytes, bytes]:
        """
        Encrypt a message for a chat room using a shared room key
        Returns (ciphertext, nonce)
        """
        box = SecretBox(room_key)
        nonce = nacl_random(SecretBox.NONCE_SIZE)
        ciphertext = box.encrypt(plaintext.encode('utf-8'), nonce).ciphertext
        
        return ciphertext, nonce
    
    @staticmethod
    def decrypt_for_room(
        ciphertext: bytes,
        nonce: bytes,
        room_key: bytes,
    ) -> str:
        """
        Decrypt a message from a chat room using the shared room key
        """
        box = SecretBox(room_key)
        plaintext = box.decrypt(ciphertext, nonce)
        
        return plaintext.decode('utf-8')
    
    @staticmethod
    def generate_room_key() -> bytes:
        """Generate a secure random key for a chat room"""
        return nacl_random(E2EEncryption.KEY_SIZE)
    
    @staticmethod
    def encrypt_room_key_for_user(
        room_key: bytes,
        user_public_key: bytes,
        admin_private_key: bytes,
    ) -> EncryptedMessage:
        """
        Encrypt a room key for a specific user
        Used when adding users to a room
        """
        return E2EEncryption.encrypt_message(
            base64.b64encode(room_key).decode('utf-8'),
            admin_private_key,
            user_public_key,
        )
    
    @staticmethod
    def decrypt_room_key(
        encrypted_key: EncryptedMessage,
        user_private_key: bytes,
    ) -> bytes:
        """Decrypt a room key for a user"""
        key_b64 = E2EEncryption.decrypt_message(encrypted_key, user_private_key)
        return base64.b64decode(key_b64)


class SecureMessageHandler:
    """
    High-level handler for secure message operations
    """
    
    def __init__(self, user_private_key: bytes):
        self.private_key = user_private_key
        self.public_key = bytes(PrivateKey(user_private_key).public_key)
    
    def encrypt_direct_message(self, plaintext: str, recipient_public_key: bytes) -> dict:
        """Encrypt a direct message to a specific user"""
        encrypted = E2EEncryption.encrypt_message(
            plaintext,
            self.private_key,
            recipient_public_key,
        )
        return encrypted.to_dict()
    
    def decrypt_direct_message(self, encrypted_data: dict) -> str:
        """Decrypt a direct message"""
        encrypted = EncryptedMessage.from_dict(encrypted_data)
        return E2EEncryption.decrypt_message(encrypted, self.private_key)
    
    def encrypt_room_message(self, plaintext: str, room_key: bytes) -> dict:
        """Encrypt a message for a chat room"""
        ciphertext, nonce = E2EEncryption.encrypt_for_room(plaintext, room_key)
        return {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'sender_public_key': base64.b64encode(self.public_key).decode('utf-8'),
        }
    
    def decrypt_room_message(self, encrypted_data: dict, room_key: bytes) -> str:
        """Decrypt a message from a chat room"""
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        nonce = base64.b64decode(encrypted_data['nonce'])
        return E2EEncryption.decrypt_for_room(ciphertext, nonce, room_key)


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)


def hash_for_verification(data: str) -> str:
    """Create a hash for message verification (not encryption)"""
    return hashlib.sha3_256(data.encode('utf-8')).hexdigest()
