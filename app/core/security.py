import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from jose import jwt
from passlib.context import CryptContext

from app.config import Settings, get_settings

type TokenType = Literal["access", "refresh"]

type Token = str
type Tokens = dict[TokenType, Token]
type Payload = dict[Any, Any]

settings: Settings = get_settings()


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


def create_jwt(payload: Payload, expires_delta: timedelta) -> str:
    """Создает JWT.

    В качестве ввода он получает информацию для кодирования и время жизни токена.

    Parameters
    ----------
    payload : Payload
        Словарь с данными.
    expires_delta : timedelta
        Время жизни токена.

    Returns
    -------
    str
        JSON Web Token.
    """
    to_encode = payload.copy()

    now: datetime = datetime.now(timezone.utc)
    to_encode.update({"iat": now, "exp": now + expires_delta})

    return _jwt_encode(to_encode)


def create_jwt_pair(
    at_payload: Payload,
    rt_payload: Payload | None = None,
    at_expires_delta: timedelta = timedelta(
        minutes=settings.ACCESS_TOKEN_LIFETIME_MINUTES,
    ),
    rt_expires_delta: timedelta = timedelta(days=settings.REFRESH_TOKEN_LIFETIME_DAYS),
) -> Tokens:
    """Создает пару JWT, состоящую из токена доступа и токена обновления.

    Parameters
    ----------
    at_payload : Payload
        Информация, которая должна быть закодирована в токене доступа.
    rt_payload : Payload | None
        Информация, которая должна быть закодирована в токене обновления.
    at_expires_delta : timedelta
        Время жизни токена доступа.
    rt_expires_delta : timedelta
        Время жизни токена обновления.

    Returns
    -------
    Tokens
        Пара JWT (токен доступа + токен обновления).
    """
    if rt_payload is None:
        rt_payload = at_payload

    return {
        "access": create_jwt(at_payload, at_expires_delta),
        "refresh": create_jwt(rt_payload, rt_expires_delta),
    }


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_(
    secret: str | bytes,
    scheme: str | None = None,
    category: str | None = None,
) -> str:
    """Прокси для метода ``CriptContext.hash()``.

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
    """Прокси для метода ``CriptContext.verify()``.

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
        ``True``, если хеш секрета соответствует переданному секрету, в ином случае ``False``.
    """
    return pwd_context.verify(secret, hashed, scheme, category)


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
