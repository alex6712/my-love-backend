from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag

from app.config import Settings, get_settings
from app.core.security import (
    create_jwt,
    create_jwt_pair,
    decrypt_data,
    encrypt_data,
    hash_,
    jwt_decode,
    verify,
)

settings: Settings = get_settings()


class TestPasswordHashing:
    """Тесты функций хеширования и верификации паролей."""

    def test_hash_creates_unique_hashes(self):
        """Одинаковые пароли должны создавать разные хеши (соль)."""
        password = "my_secure_password"
        hash1 = hash_(password)
        hash2 = hash_(password)

        assert hash1 != hash2
        assert verify(password, hash1)
        assert verify(password, hash2)

    def test_hash_verify_correct_password(self):
        """Верификация правильного пароля должна возвращать True."""
        password = "test_password_123"
        hashed = hash_(password)

        assert verify(password, hashed)

    def test_hash_verify_incorrect_password(self):
        """Верификация неправильного пароля должна возвращать False."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = hash_(password)

        assert verify(wrong_password, hashed) is False

    def test_hash_verify_with_bytes(self):
        """Хэширование должно работать с байтами."""
        password = b"bytes_password"
        hashed = hash_(password)

        assert verify(password, hashed)

    def test_hash_verify_nonexistent_password(self):
        """Проверка несуществующего пароля."""
        password = "existing_password"
        hashed = hash_(password)

        assert verify("different_password", hashed) is False

    def test_hash_unicode_password(self):
        """Поддержка unicode-паролей."""
        password = "пароль_с_эмодзи 🔐"
        hashed = hash_(password)

        assert verify(password, hashed)


class TestJWTTokens:
    """Тесты функций работы с JWT токенами."""

    def test_create_jwt_returns_string(self):
        """Создание JWT должно возвращать строку."""
        payload = {"sub": str(uuid4())}
        expires_delta = timedelta(hours=1)
        token = create_jwt(payload, expires_delta)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_jwt_decode_returns_payload(self):
        """Декодирование JWT должно возвращать payload."""
        payload = {"sub": str(uuid4()), "test": "data"}
        expires_delta = timedelta(hours=1)
        token = create_jwt(payload, expires_delta)

        decoded = jwt_decode(token)

        assert decoded["sub"] == payload.sub
        assert decoded["test"] == payload.test
        assert "iat" in decoded
        assert "exp" in decoded
        assert "jti" in decoded
        assert decoded["iss"] == "my-love-backend"

    def test_jwt_pair_contains_both_tokens(self):
        """Пара JWT должна содержать access и refresh токены."""
        payload = {"sub": str(uuid4())}
        tokens = create_jwt_pair(payload)

        assert "access" in tokens
        assert "refresh" in tokens
        assert isinstance(tokens["access"], str)
        assert isinstance(tokens["refresh"], str)
        assert len(tokens["access"]) > 0
        assert len(tokens["refresh"]) > 0

    def test_jwt_pair_different_expiration(self):
        """Access и refresh токены должны иметь разное время жизни."""
        payload = {"sub": str(uuid4())}
        tokens = create_jwt_pair(payload)

        access_payload = jwt_decode(tokens["access"])
        refresh_payload = jwt_decode(tokens["refresh"])

        assert access_payload.exp < refresh_payload.exp

    def test_jwt_pair_custom_expiration(self):
        """Пара JWT должна поддерживать кастомное время жизни."""
        payload = {"sub": str(uuid4())}
        at_delta = timedelta(minutes=5)
        rt_delta = timedelta(days=7)

        tokens = create_jwt_pair(
            payload,
            at_expires_delta=at_delta,
            rt_expires_delta=rt_delta,
        )

        access_payload = jwt_decode(tokens["access"])
        refresh_payload = jwt_decode(tokens["refresh"])

        access_exp = datetime.fromtimestamp(access_payload.exp, tz=timezone.utc)
        refresh_exp = datetime.fromtimestamp(refresh_payload.exp, tz=timezone.utc)

        assert refresh_exp - access_exp > timedelta(days=6)

    def test_jwt_expired_token_raises_error(self):
        """Просроченный токен должен вызывать ошибку при декодировании."""
        from jose import ExpiredSignatureError

        payload = {"sub": str(uuid4())}
        expires_delta = timedelta(seconds=-1)  # Уже истёк
        token = create_jwt(payload, expires_delta)

        with pytest.raises(ExpiredSignatureError):
            jwt_decode(token)

    def test_jwt_invalid_token_raises_error(self):
        """Невалидный токен должен вызывать ошибку."""
        from jose import JWTError

        invalid_token = "invalid.jwt.token"

        with pytest.raises(JWTError):
            jwt_decode(invalid_token)


class TestEncryption:
    """Тесты функций шифрования данных."""

    def test_encrypt_decrypt_roundtrip(self):
        """Шифрование и дешифрование должны восстанавливать данные."""
        key = b"0123456789abcdef" * 2  # 32 байта
        plaintext = "Секретное сообщение"

        encrypted = encrypt_data(key, plaintext)
        decrypted = decrypt_data(
            key,
            encrypted["ciphertext"],
            encrypted["iv"],
            encrypted["tag"],
        )

        assert decrypted == plaintext

    def test_encrypt_returns_all_parts(self):
        """Шифрование должно возвращать ciphertext, iv и tag."""
        key = b"0123456789abcdef" * 2
        plaintext = "Test message"

        encrypted = encrypt_data(key, plaintext)

        assert "ciphertext" in encrypted
        assert "iv" in encrypted
        assert "tag" in encrypted
        assert isinstance(encrypted["ciphertext"], bytes)
        assert isinstance(encrypted["iv"], bytes)
        assert isinstance(encrypted["tag"], bytes)

    def test_encrypt_different_iv_each_time(self):
        """Повторное шифрование того же текста должно давать разный результат."""
        key = b"0123456789abcdef" * 2
        plaintext = "Same message"

        encrypted1 = encrypt_data(key, plaintext)
        encrypted2 = encrypt_data(key, plaintext)

        assert encrypted1["ciphertext"] != encrypted2["ciphertext"]
        assert encrypted1["iv"] != encrypted2["iv"]
        assert encrypted1["tag"] != encrypted2["tag"]

    def test_encrypt_unicode(self):
        """Шифрование должно поддерживать unicode."""
        key = b"0123456789abcdef" * 2
        plaintext = "Юникод 🔐 эмодзи"

        encrypted = encrypt_data(key, plaintext)
        decrypted = decrypt_data(
            key,
            encrypted["ciphertext"],
            encrypted["iv"],
            encrypted["tag"],
        )

        assert decrypted == plaintext

    def test_encrypt_with_aad(self):
        """Шифрование должно поддерживать AAD (additional authenticated data)."""
        key = b"0123456789abcdef" * 2
        plaintext = "Message with AAD"
        aad = b"authenticated-data"

        encrypted = encrypt_data(key, plaintext, aad=aad)
        decrypted = decrypt_data(
            key,
            encrypted["ciphertext"],
            encrypted["iv"],
            encrypted["tag"],
            aad=aad,
        )

        assert decrypted == plaintext

    def test_decrypt_wrong_key_fails(self):
        """Расшифровка с неправильным ключом должна провалиться."""
        key1 = b"0123456789abcdef" * 2
        key2 = b"fedcba9876543210" * 2  # Другой ключ
        plaintext = "Secret"

        encrypted = encrypt_data(key1, plaintext)

        with pytest.raises((InvalidTag, Exception)):
            decrypt_data(
                key2,
                encrypted["ciphertext"],
                encrypted["iv"],
                encrypted["tag"],
            )
