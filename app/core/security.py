import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.core.exceptions.base import WeakServerSecretException
from app.core.types import Payload

settings = get_settings()


def _jwt_encode(payload: Payload) -> str:
    """Кодирует переданный словарь в JWT.

    Parameters
    ----------
    payload : Payload
        Словарь с данными для кодирования.

    Returns
    -------
    str
        JSON Web Token.
    """
    return jwt.encode(
        payload,
        key=settings.PRIVATE_SIGNATURE_KEY,  # type: ignore
        algorithm=settings.JWT_ALGORITHM,
    )


def jwt_decode(token: str) -> Payload:
    """Декодирует переданный JWT в словарь.

    Parameters
    ----------
    token : str
        JWT, из которого будет получен словарь.

    Returns
    -------
    Payload
        Словарь с информацией из JWT.
    """
    return jwt.decode(
        token,
        key=settings.PUBLIC_SIGNATURE_KEY,  # type: ignore
        algorithms=[settings.JWT_ALGORITHM],
    )


def create_jwt(
    sub: str,
    iat: datetime,
    *,
    exp: datetime | None = None,
    jti: str | None = None,
    iss: str = "my-love-backend",
    expires_delta: timedelta | None = None,
    **claims: Any,
) -> str:
    """Создаёт и возвращает подписанный JWT.

    Формирует payload из переданных аргументов и кодирует его.
    Значение `exp` должно быть задано одним из трёх способов -
    иначе выбрасывается `RuntimeError`.

    Parameters
    ----------
    sub : str
        Субъект токена (`sub` claim), как правило - идентификатор пользователя.
    iat : datetime
        Время выпуска токена (`iat` claim).
    exp : datetime | None, optional
        Точное время истечения токена (`exp` claim).
    jti : str | None, optional
        Уникальный идентификатор токена (`jti` claim).
        По умолчанию генерируется автоматически через `uuid.uuid4()`.
    iss : str, optional
        Издатель токена (`iss` claim). По умолчанию `"my-love-backend"`.
    expires_delta : timedelta | None, optional
        Время жизни токена относительно `iat`.
        Если передан вместе с `exp`, то `expires_delta` перезапишет `exp`.
    **claims : Any
        Дополнительные произвольные claims, которые будут добавлены в payload.
        Также может содержать `exp` как fallback.

    Returns
    -------
    str
        Подписанный JSON Web Token.

    Raises
    ------
    RuntimeError
        Если ни один из источников для `exp` не передан:
        ни `exp`, ни `expires_delta`, ни `exp` внутри `**claims`.

    Notes
    -----
    Приоритет установки `exp` claim от высшего к низшему:
    1. Высочайший приоритет: `expires_delta`.
    2. Средний приоритет: `exp` преданный по ключевому слову в claims.
    3. Наименьший приоритет: аргумент `exp`.
    """
    if not exp and not expires_delta and not claims.get("exp"):
        raise RuntimeError(
            "There's no source to set the 'exp' value from!\n"
            "You can pass it via 'exp' argument directly, via"
            "'expires_delta' argument for calculate from 'iat'"
            "and via the kwargs."
        )

    if jti is None:
        jti = str(uuid.uuid4())

    to_encode: Payload = {"sub": sub, "iat": iat, "exp": exp, "jti": jti, "iss": iss}
    to_encode.update(claims)

    if expires_delta:
        to_encode.update({"exp": iat + expires_delta})

    return _jwt_encode(to_encode)


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_(
    secret: str | bytes,
    scheme: str | None = None,
    category: str | None = None,
) -> str:
    """Прокси для метода `CriptContext.hash()`.

    Получает параметры, необходимые для выполнения хеширования, и возвращает результат.

    Parameters
    ----------
    secret : str | bytes
        Секрет для хеширования.
    scheme : str | None
        Схема, по которой хеширование будет выполнено. Необязательный аргумент.
        Если не передан, используется схема по умолчанию.

        .. deprecated:: 1.7
            Поддержка этого ключевого слова устарела и будет удалена в PassLib 2.0.
    category : str | None
        Если передано, то любые значения по умолчанию, связанные с категорией
        будут изменены на значения по умолчанию для этой категории.

    Returns
    -------
    str
        Хеш секрета в соответствии с установленной схемой и настройками.
    """
    return pwd_context.hash(secret, scheme, category)


def verify(
    secret: str | bytes,
    hashed: str | bytes,
    scheme: str | None = None,
    category: str | None = None,
) -> bool:
    """Прокси для метода `CriptContext.verify()`.

    Проверяет переданный секрет на соответствие хешу.

    Parameters
    ----------
    secret : str | bytes
        Секрет для проверки.
    hashed : str | bytes
        Хеш секрета.
    scheme : str | None
        Схема, по которой хеширование будет выполнено. Необязательный аргумент.
        Если не передан, используется схема по умолчанию.

        .. deprecated:: 1.7
            Поддержка этого ключевого слова устарела и будет удалена в PassLib 2.0.
    category : str | None
        Если передано, то любые значения по умолчанию, связанные с категорией
        будут изменены на значения по умолчанию для этой категории.

    Returns
    -------
    bool
        `True`, если хеш секрета соответствует переданному секрету, в ином случае `False`.
    """
    return pwd_context.verify(secret, hashed, scheme, category)


def hash_token(
    token: str, secret_key: bytes = settings.HMAC_SECRET_KEY.encode()
) -> str:
    """Создаёт детерминированный HMAC-SHA256 хеш токена.

    В отличие от `hash_()`, результат детерминирован — одинаковый токен
    всегда даёт одинаковый хеш, что позволяет искать сессию по хешу в БД.
    Используется исключительно для хеширования refresh токенов.

    Parameters
    ----------
    token : str
        Токен для хеширования.
    secret_key : bytes, optional
        Секретный ключ для HMAC. По умолчанию используется значение
        из настроек приложения. Длина ключа должна быть не менее 32 байт.

    Returns
    -------
    str
        HMAC-SHA256 хеш токена в виде hex-строки.

    Raises
    ------
    WeakServerSecretException
        Если длина секретного ключа меньше 32 байт.
    """
    if len(secret_key) < 32:
        raise WeakServerSecretException(
            detail=(
                f"HMAC secret key is too weak: expected at least 32 bytes, got {len(secret_key)}."
            )
        )

    return hmac.new(
        secret_key,
        token.encode(),
        hashlib.sha256,
    ).hexdigest()


def encrypt_data(
    key: bytes, plaintext: str, aad: bytes | None = None
) -> dict[str, bytes]:
    """Шифрует строку данных с использованием AES-256 в режиме GCM.

    Parameters
    ----------
    key : bytes
        Ключ шифрования (256 бит).
    plaintext : str
        Строка данных для шифрования.
    aad : bytes | None
        Дополнительные аутентифицируемые данные.

    Returns
    -------
    dict[str, bytes]
        Словарь с результатами шифрования
        - ciphertext, зашифрованные данные
        - iv, вектор инициализации
        - tag, аутентификационный тег
    """
    iv = os.urandom(12)

    cipher = Cipher(algorithms.AES256(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    if aad:
        encryptor.authenticate_additional_data(aad)

    ciphertext = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()

    return {"ciphertext": ciphertext, "iv": iv, "tag": encryptor.tag}


def decrypt_data(
    key: bytes,
    ciphertext: bytes,
    iv: bytes,
    tag: bytes,
    aad: bytes | None = None,
) -> str:
    """Дешифрует ранее зашифрованные данные.

    Parameters
    ----------
    key : bytes
        Ключ шифрования (256 бит).
    ciphertext : bytes
        Зашифрованные данные.
    iv : bytes
        Использованный при шифровании вектор инициализации.
    tag : bytes
        Аутентификационный тег.
    aad : bytes | None
        Дополнительные аутентифицируемые данные.

    Returns
    -------
    str
        Расшифрованная строка.
    """
    cipher = Cipher(
        algorithms.AES256(key), modes.GCM(iv, tag), backend=default_backend()
    )
    decryptor = cipher.decryptor()

    if aad:
        decryptor.authenticate_additional_data(aad)

    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return plaintext.decode("utf-8")
