from typing import Annotated, Any, Callable, Coroutine

from fastapi import Depends, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)

from app.config import get_settings
from app.core.dependencies.services import ServiceManagerDependency
from app.core.exceptions.auth import AuthDomainException
from app.schemas.dto.payload import AccessTokenPayload

SignInCredentialsDependency = Annotated[OAuth2PasswordRequestForm, Depends()]
"""Зависимость на получение реквизитов для входа в систему."""

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"/{settings.CURRENT_API_PATH}/auth/login",
    auto_error=False,
)


def dependency(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(HTTPBearer(auto_error=False))
    ],
) -> str | None:
    """Функция-зависимость на получение значения токена обновления.

    Parameters
    ----------
    credentials : HTTPAuthorizationCredentials | None
        Учётные данные, полученные из HTTP Bearer-токена.

    Returns
    -------
    str | None
        Значение токена обновления либо None, если токен отсутствует.

    Notes
    -----
    Из объекта HTTPAuthorizationCredentials извлекается только поле
    `credentials`, содержащее сам токен. Поле `scheme` игнорируется.
    """
    return credentials.credentials if credentials else None


ExtractAccessTokenDependency = Annotated[str | None, Depends(oauth2_scheme)]
"""Зависимость на получение токена доступа из заголовков запроса."""

ExtractRefreshTokenDependency = Annotated[str | None, Depends(dependency)]
"""Зависимость на получение токена обновления из заголовков запроса."""

AuthDependencyCallable = Callable[
    [ExtractAccessTokenDependency, ServiceManagerDependency],
    Coroutine[Any, Any, AccessTokenPayload | None],
]
"""Тип вызываемого объекта зависимости аутентификации."""


def check_auth(strict: bool) -> AuthDependencyCallable:
    """Фабрика для создания зависимостей аутентификации.

    Генерирует зависимости FastAPI с гибким поведением при ошибках
    аутентификации. Позволяет выбирать между строгим и мягким режимом
    проверки access token.

    Parameters
    ----------
    strict : bool
        Режим обработки ошибок:
        - True: строгий режим - исключение пробрасывается.
        - False: мягкий режим - при ошибке возвращается None.

    Returns
    -------
    AuthDependencyCallable
        Функция зависимости, использующая ServiceManager
        для доступа к AuthService.

    See Also
    --------
    SoftAuthenticationDependency
    StrictAuthenticationDependency
    """

    async def dependency(
        access_token: ExtractAccessTokenDependency,
        services: ServiceManagerDependency,
    ) -> AccessTokenPayload | None:
        """Внутренняя функция зависимости, выполняющая проверку токена.

        Parameters
        ----------
        access_token : str | None
            JWT access token, извлечённый из заголовков запроса.
        services : ServiceManagerDependency
            Менеджер сервисов уровня запроса.

        Returns
        -------
        AccessTokenPayload | None
            Расшифрованные данные токена при успешной проверке.
            В мягком режиме при ошибке возвращается None.

        Raises
        ------
        AuthDomainException
            В строгом режиме при ошибке аутентификации.

        Notes
        -----
        Поведение:
        1. В строгом режиме доменные исключения пробрасываются.
        2. В мягком режиме AuthDomainException преобразуется в None.
        3. Недоменные исключения никогда не подавляются.
        """
        try:
            return await services.auth.validate_access_token(access_token)
        except AuthDomainException as e:
            if strict:
                raise e
            return None

    return dependency


SoftAuthenticationDependency = Annotated[
    AccessTokenPayload | None, Depends(check_auth(strict=False))
]
"""Зависимость для мягкой проверки аутентификации.

Используется в эндпоинтах, доступных как аутентифицированным,
так и неаутентифицированным пользователям.
"""

StrictAuthenticationDependency = Annotated[
    AccessTokenPayload, Depends(check_auth(strict=True))
]
"""Зависимость для строгой проверки аутентификации.

Используется в защищённых эндпоинтах,
требующих обязательной аутентификации.
"""
