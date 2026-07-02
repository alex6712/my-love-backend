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
from app.core.types import TokenType
from app.schemas.dto.payload import (
    AccessTokenPayload,
    AnyTokenPayload,
    RefreshTokenPayload,
)

_settings = get_settings()


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
        key=_settings.PRIVATE_SIGNATURE_KEY.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        ),
        algorithm=_settings.JWT_ALGORITHM,
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
    token_type : TokenType
        Тип токена для декодировки.

    Returns
    -------
    AnyTokenPayload
        Словарь с информацией из JWT.
    """
    decoded = jwt.decode(
        token,
        key=_settings.PUBLIC_SIGNATURE_KEY.public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ),
        algorithms=[_settings.JWT_ALGORITHM],
    )

    match token_type:
        case "access":
            return AccessTokenPayload.model_validate(decoded)
        case "refresh":
            return RefreshTokenPayload.model_validate(decoded)

    raise ValueError(
        f"Cannot decode a payload for {token_type} token type."
        "It's value must be 'access' or 'refresh'."
    )


@overload
def construct_payload(
    sub: UUID,
    iat: datetime,
    sid: UUID,
    *,
    token_type: Literal["refresh"],
    exp: datetime | None = ...,
    jti: UUID | None = ...,
    iss: str = ...,
    expires_delta: timedelta | None = ...,
) -> RefreshTokenPayload: ...


@overload
def construct_payload(
    sub: UUID,
    iat: datetime,
    sid: UUID,
    *,
    token_type: Literal["access"],
    exp: datetime | None = ...,
    jti: UUID | None = ...,
    iss: str = ...,
    expires_delta: timedelta | None = ...,
) -> AccessTokenPayload: ...


def construct_payload(
    sub: UUID,
    iat: datetime,
    sid: UUID,
    *,
    token_type: TokenType,
    exp: datetime | None = None,
    jti: UUID | None = None,
    iss: str = "my-love-backend",
    expires_delta: timedelta | None = None,
) -> AnyTokenPayload:
    """Формирует и возвращает payload JWT-токена.

    Содержит всю логику построения payload, вынесенную из `create_jwt`.
    Тип возвращаемого payload зависит от значения `token_type`:
    если передан `"refresh"` - возвращается `RefreshTokenPayload`,
    если `"access"` - `AccessTokenPayload`, если значение иное, то вызывается
    `ValueError`.

    Parameters
    ----------
    sub : UUID
        Субъект токена - идентификатор пользователя.
    iat : datetime
        Время выпуска токена.
    sid : UUID
        Идентификатор сессии пользователя.
    token_type : TokenType
        Тип токена, для которого создаётся полезная нагрузка:
        - `"access"` - возвращается `AccessTokenPayload`;
        - `"refresh"` - возвращается `RefreshTokenPayload`.
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

    Returns
    -------
    AnyTokenPayload
        Сформированный payload - `AccessTokenPayload` или `RefreshTokenPayload`.

    Raises
    ------
    RuntimeError
        Если не передан ни `exp`, ни `expires_delta`.
    ValueError
        Если переданное значение параметра `token_type` неизвестно.

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
        "sid": sid,
    }

    match token_type:
        case "access":
            return AccessTokenPayload(**data)
        case "refresh":
            return RefreshTokenPayload(**data)

    raise ValueError(
        f"Cannot build a payload for {token_type} token type."
        "It's value must be 'access' or 'refresh'."
    )


@overload
def create_jwt(
    sub_or_payload: RefreshTokenPayload, *, token_type: Literal["refresh"]
) -> str: ...


@overload
def create_jwt(
    sub_or_payload: AccessTokenPayload, *, token_type: Literal["access"]
) -> str: ...


@overload
def create_jwt(
    sub_or_payload: UUID,
    iat: datetime,
    sid: UUID,
    *,
    token_type: TokenType,
    exp: datetime | None = ...,
    jti: UUID | None = ...,
    iss: str = ...,
    expires_delta: timedelta | None = ...,
) -> str: ...


def create_jwt(
    sub_or_payload: UUID | AnyTokenPayload,
    iat: datetime | None = None,
    sid: UUID | None = None,
    *,
    token_type: TokenType,
    exp: datetime | None = None,
    jti: UUID | None = None,
    iss: str = "my-love-backend",
    expires_delta: timedelta | None = None,
) -> str:
    """Создаёт и возвращает подписанный JWT.

    Поддерживает два режима вызова:

    1. Передача готового payload-объекта (`AnyTokenPayload`) -
       полезно, когда payload уже сформирован заранее через `construct_payload`.

    2. Передача сырых значений - payload формируется внутри через
       `construct_payload`. Время истечения токена `exp` вычисляется одним из
       двух способов; если ни один не передан, выбрасывается `RuntimeError`.

    Parameters
    ----------
    sub_or_payload : UUID | AnyTokenPayload
        Либо субъект токена (идентификатор пользователя) при сырых значениях,
        либо готовый payload-объект.
    iat : datetime | None, optional
        Время выпуска токена. Обязателен при передаче сырых значений.
    sid : UUID | None, optional
        Идентификатор сессии пользователя. Обязателен при передаче сырых значений.
    token_type : TokenType
        Тип токена, для которого создаётся полезная нагрузка:
        - `"access"` - возвращается `AccessTokenPayload`;
        - `"refresh"` - возвращается `RefreshTokenPayload`.
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

    Returns
    -------
    str
        Подписанный JSON Web Token.

    Raises
    ------
    RuntimeError
        Если не передан ни `exp`, ни `expires_delta` при использовании
        сырых значений.
    TypeError
        Если `sub_or_payload` является `UUID`, но `iat` или `sid`
        не переданы.

    Notes
    -----
    Если переданы оба аргумента `exp` и `expires_delta`,
    приоритет имеет `expires_delta`.
    """
    if isinstance(sub_or_payload, (AccessTokenPayload, RefreshTokenPayload)):
        return _jwt_encode(sub_or_payload)

    if iat is None or sid is None:
        raise TypeError("'iat' and 'sid' are required when 'sub_or_payload' is UUID.")

    payload = construct_payload(
        sub_or_payload,
        iat,
        sid,
        token_type=token_type,
        exp=exp,
        jti=jti,
        iss=iss,
        expires_delta=expires_delta,
    )

    return _jwt_encode(payload)


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
    token: str, secret_key: bytes = _settings.HMAC_SECRET_KEY.encode()
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

    return hmac.new(secret_key, token.encode(), hashlib.sha256).hexdigest()


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
    key: bytes, ciphertext: bytes, iv: bytes, tag: bytes, aad: bytes | None = None
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
