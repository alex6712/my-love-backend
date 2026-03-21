import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Literal, overload
from uuid import UUID

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.core.exceptions.base import WeakServerSecretException
from app.core.types import UNSET, Maybe, TokenType, Unset
from app.schemas.dto.payload import (
    AccessTokenPayload,
    AnyTokenPayload,
    RefreshTokenPayload,
)

settings = get_settings()


def _jwt_encode(payload: AnyTokenPayload) -> str:
    """Кодирует переданный словарь в JWT.

    Parameters
    ----------
    payload : AnyTokenPayload
        Словарь с данными для кодирования.

    Returns
    -------
    str
        JSON Web Token.
    """
    return jwt.encode(
        payload.to_jwt_payload(),
        key=settings.PRIVATE_SIGNATURE_KEY.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        ),
        algorithm=settings.JWT_ALGORITHM,
    )


@overload
def jwt_decode(token: str, token_type: Literal["access"]) -> AccessTokenPayload: ...


@overload
def jwt_decode(token: str, token_type: Literal["refresh"]) -> RefreshTokenPayload: ...


def jwt_decode(token: str, token_type: TokenType) -> AnyTokenPayload:
    """Декодирует переданный JWT в словарь.

    Parameters
    ----------
    token : str
        JWT, из которого будет получен словарь.

    Returns
    -------
    AnyTokenPayload
        Словарь с информацией из JWT.
    """
    decoded = jwt.decode(
        token,
        key=settings.PUBLIC_SIGNATURE_KEY.public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ),
        algorithms=[settings.JWT_ALGORITHM],
    )

    if token_type == "access":
        return AccessTokenPayload.model_validate(decoded)

    return RefreshTokenPayload.model_validate(decoded)


def create_jwt(
    sub: UUID,
    iat: datetime,
    session_id: UUID,
    *,
    exp: datetime | None = None,
    jti: UUID | None = None,
    iss: str = "my-love-backend",
    expires_delta: timedelta | None = None,
    couple_id: Maybe[UUID | None] = UNSET,
) -> str:
    """Создаёт и возвращает подписанный JWT.

    Формирует payload из переданных аргументов и передаёт его в `_jwt_encode`.
    Время истечения токена `exp` вычисляется одним из двух способов -
    если ни один не передан, выбрасывается `RuntimeError`.

    Parameters
    ----------
    sub : UUID
        Субъект токена - идентификатор пользователя.
    iat : datetime
        Время выпуска токена.
    session_id : UUID
        Идентификатор сессии пользователя.
    exp : datetime | None, optional
        Точное время истечения токена.
        Игнорируется, если передан `expires_delta`.
    jti : UUID | None, optional
        Уникальный идентификатор токена.
        Если не передан - генерируется автоматически через `uuid.uuid4()`.
    iss : str, optional
        Издатель токена. По умолчанию `"my-love-backend"`.
    expires_delta : timedelta | None, optional
        Время жизни токена относительно `iat`.
        Имеет приоритет над `exp`, если передан.
    couple_id : Maybe[UUID | None], optional
        Опциональный доменный claim, добавляемый только в access-токен.

        Используется для передачи дополнительного контекста авторизации,
        связанного с пользователем (идентификатора пары пользователя).

        Поведение зависит от переданного значения:
        - UNSET - claim не добавляется в payload (используется refresh-токен);
        - UUID - claim добавляется с указанным значением;
        - None - claim добавляется с null-значением.

    Returns
    -------
    str
        Подписанный JSON Web Token.

    Raises
    ------
    RuntimeError
        Если не передан ни `exp`, ни `expires_delta`.

    Notes
    -----
    Если переданы оба аргумента `exp` и `expires_delta`,
    приоритет имеет `expires_delta`.
    """
    if expires_delta is not None:
        resolved_exp = iat + expires_delta
    elif exp is not None:
        resolved_exp = exp
    else:
        raise RuntimeError(
            "There's no source to set the 'exp' value from!\n"
            "You can pass it via 'exp' argument directly or via"
            "'expires_delta' argument for calculate from 'iat'."
        )

    if jti is None:
        jti = uuid.uuid4()

    data: dict[str, Any] = {
        "sub": sub,
        "iat": iat,
        "exp": resolved_exp,
        "jti": jti,
        "iss": iss,
        "session_id": session_id,
    }

    if not isinstance(couple_id, Unset):
        to_encode = AccessTokenPayload(**data, couple_id=couple_id)
    else:
        to_encode = RefreshTokenPayload(**data)

    return _jwt_encode(to_encode)


_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_(
    secret: str | bytes,
    scheme: str | None = None,
    category: str | None = None,
) -> str:
    """Прокси для метода `CryptContext.hash()`.

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
        Хэш секрета в соответствии с установленной схемой и настройками.
    """
    return _pwd_context.hash(secret, scheme, category)


def verify(
    secret: str | bytes,
    hashed: str | bytes,
    scheme: str | None = None,
    category: str | None = None,
) -> bool:
    """Прокси для метода `CryptContext.verify()`.

    Проверяет переданный секрет на соответствие хешу.

    Parameters
    ----------
    secret : str | bytes
        Секрет для проверки.
    hashed : str | bytes
        Хэш секрета.
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
    return _pwd_context.verify(secret, hashed, scheme, category)


def hash_token(
    token: str, secret_key: bytes = settings.HMAC_SECRET_KEY.encode()
) -> str:
    """Создаёт детерминированный HMAC-SHA256 хеш токена.

    В отличие от `hash_()`, результат детерминирован - одинаковый токен
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
