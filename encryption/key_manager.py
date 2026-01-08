"""
Key Management System for Secure Chat
Handles secure storage and rotation of encryption keys
"""

import os
import base64
import json
from typing import Optional, Dict
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from .e2e_crypto import E2EEncryption, KeyPair, generate_secure_token


class KeyManager:
    """
    Manages encryption keys for users and rooms
    Provides secure key storage and rotation capabilities
    """
    
    KEY_VERSION = 1
    ROTATION_INTERVAL_DAYS = 30
    
    def __init__(self, master_password: str, salt: Optional[bytes] = None):
        """
        Initialize KeyManager with a master password
        The master password is used to encrypt all stored keys
        """
        self.salt = salt or os.urandom(16)
        self._derive_master_key(master_password)
    
    def _derive_master_key(self, password: str):
        """Derive the master encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=480000,  # High iteration count for security
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self._fernet = Fernet(key)
    
    def encrypt_key(self, key_data: bytes) -> str:
        """Encrypt a key for secure storage"""
        return self._fernet.encrypt(key_data).decode('utf-8')
    
    def decrypt_key(self, encrypted_key: str) -> bytes:
        """Decrypt a stored key"""
        return self._fernet.decrypt(encrypted_key.encode('utf-8'))
    
    def generate_user_keys(self) -> Dict[str, str]:
        """
        Generate a new key pair for a user
        Returns encrypted keys ready for database storage
        """
        key_pair = E2EEncryption.generate_key_pair()
        
        return {
            'private_key_encrypted': self.encrypt_key(key_pair.private_key),
            'public_key': base64.b64encode(key_pair.public_key).decode('utf-8'),
            'key_version': self.KEY_VERSION,
            'created_at': datetime.utcnow().isoformat(),
        }
    
    def get_user_keys(self, encrypted_private_key: str, public_key_b64: str) -> KeyPair:
        """
        Retrieve and decrypt user keys
        """
        private_key = self.decrypt_key(encrypted_private_key)
        public_key = base64.b64decode(public_key_b64)
        
        return KeyPair(private_key=private_key, public_key=public_key)
    
    def generate_room_key(self) -> Dict[str, str]:
        """
        Generate a new encryption key for a chat room
        """
        room_key = E2EEncryption.generate_room_key()
        
        return {
            'key_encrypted': self.encrypt_key(room_key),
            'key_id': generate_secure_token(16),
            'key_version': self.KEY_VERSION,
            'created_at': datetime.utcnow().isoformat(),
        }
    
    def get_room_key(self, encrypted_key: str) -> bytes:
        """Retrieve and decrypt a room key"""
        return self.decrypt_key(encrypted_key)
    
    def should_rotate_key(self, created_at: str) -> bool:
        """Check if a key should be rotated based on age"""
        created = datetime.fromisoformat(created_at)
        age = datetime.utcnow() - created
        return age > timedelta(days=self.ROTATION_INTERVAL_DAYS)
    
    def rotate_room_key(self, old_encrypted_key: str) -> Dict[str, str]:
        """
        Rotate a room key
        Returns new key data
        Note: Messages encrypted with old key need to be re-encrypted
        """
        # Generate new key
        new_key_data = self.generate_room_key()
        new_key_data['previous_key_encrypted'] = old_encrypted_key
        
        return new_key_data
    
    def export_public_key_bundle(self, public_key: str) -> str:
        """
        Export public key in a shareable format
        Used for key verification between users
        """
        bundle = {
            'public_key': public_key,
            'algorithm': 'X25519',
            'version': self.KEY_VERSION,
            'exported_at': datetime.utcnow().isoformat(),
        }
        return base64.urlsafe_b64encode(json.dumps(bundle).encode()).decode()
    
    def import_public_key_bundle(self, bundle_str: str) -> str:
        """Import a public key from a bundle"""
        bundle = json.loads(base64.urlsafe_b64decode(bundle_str))
        return bundle['public_key']


class SessionKeyManager:
    """
    Manages ephemeral session keys for Perfect Forward Secrecy
    Each session gets a unique key derived from the main keys
    """
    
    def __init__(self, user_private_key: bytes, session_id: str):
        self.session_id = session_id
        self.user_private_key = user_private_key
        self._session_keys: Dict[str, bytes] = {}
    
    def derive_session_key(self, peer_public_key: bytes, context: str = '') -> bytes:
        """
        Derive a unique session key for communication with a peer
        Provides Perfect Forward Secrecy
        """
        # Create a unique context for this session
        session_context = f"{self.session_id}:{context}".encode()
        
        # Get base shared secret
        base_key = E2EEncryption.derive_shared_secret(
            self.user_private_key,
            peer_public_key,
        )
        
        # Derive session-specific key using HKDF
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=session_context,
            info=b'session_key_v1',
            backend=default_backend(),
        )
        
        session_key = hkdf.derive(base_key)
        
        # Cache for performance
        cache_key = base64.b64encode(peer_public_key).decode()
        self._session_keys[cache_key] = session_key
        
        return session_key
    
    def get_cached_session_key(self, peer_public_key: bytes) -> Optional[bytes]:
        """Get a cached session key if available"""
        cache_key = base64.b64encode(peer_public_key).decode()
        return self._session_keys.get(cache_key)
    
    def clear_session_keys(self):
        """Clear all cached session keys"""
        self._session_keys.clear()


def create_key_fingerprint(public_key: bytes) -> str:
    """
    Create a human-readable fingerprint for key verification
    Users can compare fingerprints to verify each other's identity
    """
    import hashlib
    
    digest = hashlib.sha256(public_key).digest()
    
    # Format as groups of 4 hex characters
    hex_str = digest.hex().upper()
    groups = [hex_str[i:i+4] for i in range(0, 32, 4)]  # First 32 chars
    
    return ' '.join(groups)
