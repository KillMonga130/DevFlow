"""
Unit tests for encryption utilities.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.memory.utils.encryption import (
    get_encryption_key, encrypt_sensitive_data, decrypt_sensitive_data
)


class TestGetEncryptionKey:
    """Test get_encryption_key function."""
    
    def test_get_encryption_key_with_config(self):
        """Test getting encryption key when configured."""
        with patch('src.memory.utils.encryption.get_memory_config') as mock_config:
            mock_config.return_value.encryption_key = "test-key-123"
            
            key = get_encryption_key()
            
            assert key == b"test-key-123"
    
    def test_get_encryption_key_no_config(self):
        """Test getting encryption key when not configured."""
        with patch('src.memory.utils.encryption.get_memory_config') as mock_config:
            mock_config.return_value.encryption_key = None
            
            key = get_encryption_key()
            
            assert key is None
    
    def test_get_encryption_key_empty_string(self):
        """Test getting encryption key with empty string."""
        with patch('src.memory.utils.encryption.get_memory_config') as mock_config:
            mock_config.return_value.encryption_key = ""
            
            key = get_encryption_key()
            
            # Empty string is treated as falsy, so returns None
            assert key is None


class TestEncryptSensitiveData:
    """Test encrypt_sensitive_data function."""
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    def test_encrypt_with_key(self, mock_get_key):
        """Test encryption when key is available."""
        # Mock a valid Fernet key
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key()
        mock_get_key.return_value = test_key
        
        data = "sensitive information"
        encrypted = encrypt_sensitive_data(data)
        
        # Should be different from original and be a string
        assert encrypted != data
        assert isinstance(encrypted, str)
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    def test_encrypt_without_key(self, mock_get_key):
        """Test encryption when no key is configured."""
        mock_get_key.return_value = None
        
        data = "sensitive information"
        encrypted = encrypt_sensitive_data(data)
        
        # Should return original data when no key
        assert encrypted == data
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    def test_encrypt_empty_string(self, mock_get_key):
        """Test encrypting empty string."""
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key()
        mock_get_key.return_value = test_key
        
        data = ""
        encrypted = encrypt_sensitive_data(data)
        
        # Should handle empty string
        assert isinstance(encrypted, str)
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    @patch('src.memory.utils.encryption.Fernet')
    def test_encrypt_fernet_error(self, mock_fernet_class, mock_get_key):
        """Test encryption when Fernet raises an error."""
        mock_get_key.return_value = b"test-key"
        mock_fernet_instance = MagicMock()
        mock_fernet_instance.encrypt.side_effect = Exception("Encryption failed")
        mock_fernet_class.return_value = mock_fernet_instance
        
        data = "test data"
        encrypted = encrypt_sensitive_data(data)
        
        # Should return original data on error
        assert encrypted == data


class TestDecryptSensitiveData:
    """Test decrypt_sensitive_data function."""
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    def test_decrypt_with_key(self, mock_get_key):
        """Test decryption when key is available."""
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key()
        mock_get_key.return_value = test_key
        
        # First encrypt some data
        original_data = "sensitive information"
        encrypted = encrypt_sensitive_data(original_data)
        
        # Then decrypt it
        decrypted = decrypt_sensitive_data(encrypted)
        
        assert decrypted == original_data
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    def test_decrypt_without_key(self, mock_get_key):
        """Test decryption when no key is configured."""
        mock_get_key.return_value = None
        
        data = "some encrypted data"
        decrypted = decrypt_sensitive_data(data)
        
        # Should return original data when no key
        assert decrypted == data
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    @patch('src.memory.utils.encryption.Fernet')
    def test_decrypt_fernet_error(self, mock_fernet_class, mock_get_key):
        """Test decryption when Fernet raises an error."""
        mock_get_key.return_value = b"test-key"
        mock_fernet_instance = MagicMock()
        mock_fernet_instance.decrypt.side_effect = Exception("Decryption failed")
        mock_fernet_class.return_value = mock_fernet_instance
        
        data = "encrypted data"
        decrypted = decrypt_sensitive_data(data)
        
        # Should return original data on error
        assert decrypted == data
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    def test_decrypt_invalid_data(self, mock_get_key):
        """Test decryption with invalid encrypted data."""
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key()
        mock_get_key.return_value = test_key
        
        invalid_data = "not-encrypted-data"
        decrypted = decrypt_sensitive_data(invalid_data)
        
        # Should return original data when decryption fails
        assert decrypted == invalid_data


class TestEncryptionIntegration:
    """Test encryption integration scenarios."""
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    def test_encrypt_decrypt_roundtrip(self, mock_get_key):
        """Test full encrypt/decrypt roundtrip."""
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key()
        mock_get_key.return_value = test_key
        
        original_data = "sensitive information"
        
        # Encrypt then decrypt
        encrypted = encrypt_sensitive_data(original_data)
        decrypted = decrypt_sensitive_data(encrypted)
        
        assert decrypted == original_data
        assert encrypted != original_data
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    def test_encrypt_decrypt_unicode(self, mock_get_key):
        """Test encryption/decryption with unicode data."""
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key()
        mock_get_key.return_value = test_key
        
        unicode_data = "Hello 世界 🌍 émojis"
        
        encrypted = encrypt_sensitive_data(unicode_data)
        decrypted = decrypt_sensitive_data(encrypted)
        
        assert decrypted == unicode_data
    
    @patch('src.memory.utils.encryption.get_encryption_key')
    def test_encrypt_decrypt_large_data(self, mock_get_key):
        """Test encryption/decryption with large data."""
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key()
        mock_get_key.return_value = test_key
        
        large_data = "x" * 10000  # 10KB of data
        
        encrypted = encrypt_sensitive_data(large_data)
        decrypted = decrypt_sensitive_data(encrypted)
        
        assert decrypted == large_data
    
    def test_no_key_roundtrip(self):
        """Test that data passes through unchanged when no key is configured."""
        with patch('src.memory.utils.encryption.get_encryption_key', return_value=None):
            original_data = "test data"
            
            encrypted = encrypt_sensitive_data(original_data)
            decrypted = decrypt_sensitive_data(encrypted)
            
            assert encrypted == original_data
            assert decrypted == original_data
    
    @patch('src.memory.utils.encryption.get_memory_config')
    def test_config_integration(self, mock_config):
        """Test integration with configuration system."""
        # Test with encryption key configured
        mock_config.return_value.encryption_key = "test-encryption-key"
        
        key = get_encryption_key()
        assert key == b"test-encryption-key"
        
        # Test without encryption key
        mock_config.return_value.encryption_key = None
        
        key = get_encryption_key()
        assert key is None


if __name__ == "__main__":
    pytest.main([__file__])