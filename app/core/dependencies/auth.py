from typing import Annotated, Any, Callable, Coroutine

from fastapi import Depends, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)

from app.config import Settings, get_settings
from app.core.dependencies.services import AuthServiceDependency
from app.core.exceptions.auth import AuthDomainException
from app.core.security import Payload

SignInCredentialsDependency = Annotated[OAuth2PasswordRequestForm, Depends()]
"""Зависимость на получение реквизитов для входа в систему"""

settings: Settings = get_settings()

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
    credentials : HTTPAuthorizationCredentials
        Учётные данные, полученные из HTTP Bearer-токена.

    Returns
    -------
    str | None
        Значение токена обновления.

    Notes
    -----
    Функция используется для получения конкретного значение токена обновления из
    объекта учётных данных HTTPAuthorizationCredentials, которы имеет два поля:
    - `scheme`: схема предоставления токена (в данном случае всегда HTTP Bearer);
    - `credentials`: строка, содержащая значение токена.

    Данные о схеме бесполезны, учитывая, что они в этом случае принимают лишь одно
    значение. Эта функция достаёт из объекта учётных данных только необходимый
    токен обновления.
    """
    return credentials.credentials if credentials else None


ExtractAccessTokenDependency = Annotated[str | None, Depends(oauth2_scheme)]
"""Зависимость на получение токена доступа из заголовков запроса."""

ExtractRefreshTokenDependency = Annotated[str | None, Depends(dependency)]
"""Зависимость на получение токена обновления из заголовков запроса."""

type AuthDependencyCallable = Callable[
    [ExtractAccessTokenDependency, AuthServiceDependency],
    Coroutine[Any, Any, Payload | None],
]
"""Тип для вызываемого объекта зависимости аутентификации"""


def check_auth(strict: bool = True) -> AuthDependencyCallable:
    """Фабрика для создания зависимостей аутентификации.

    Генерирует зависимости FastAPI с гибким поведением при ошибках аутентификации.
    Позволяет выбирать между строгим и мягким режимом проверки токена.

    Parameters
    ----------
    strict : bool, optional
        Определяет режим обработки ошибок аутентификации:
        - `True` (по умолчанию): строгий режим - выбрасывает StarletteHTTPException
        - `False`: мягкий режим - возвращает None при ошибках

    Returns
    -------
    AuthDependencyCallable
        Функция, использующая `AuthServiceDependency` для проверки аутентификации
        пользователя.

    See Also
    --------
    SoftAuthenticationDependency : Готовая зависимость для мягкой проверки
    StrictAuthenticationDependency : Готовая зависимость для строгой проверки
    """

    async def dependency(
        access_token: ExtractAccessTokenDependency, auth_service: AuthServiceDependency
    ) -> Payload | None:
        """Внутренняя функция зависимости, выполняющая проверку аутентификации.

        Реализует основную логику проверки JWT токена и обработки ошибок
        в соответствии с выбранным режимом.

        Parameters
        ----------
        auth_service : AuthServiceDependency
            Сервис аутентификации, внедряемый через DI контейнер FastAPI.
            Используется для проверки валидности access token.

        Returns
        -------
        Payload | None
            Расшифрованные данные токена (Payload) при успешной проверке.
            None возвращается только в мягком режиме при ошибке аутентификации.

        Raises
        ------
        UserDomainException
            В строгом режиме (strict=True).

        Notes
        -----
        Важные аспекты поведения:
        1. В строгом режиме НЕ перехватываются не доменные исключения
        2. В мягком режиме ЛЮБЫЕ UserDomainException преобразуются в None
        3. Не-HTTP исключения всегда пробрасываются выше
        """
        try:
            return await auth_service.validate_access_token(access_token)
        except AuthDomainException as e:
            if strict:
                raise e

            return None

    return dependency


SoftAuthenticationDependency = Annotated[
    Payload | None, Depends(check_auth(strict=False))
]
"""Зависимость для **мягкой** проверки аутентификации.

Предназначена для эндпоинтов, доступных как аутентифицированным,
так и неаутентифицированным пользователям (например, /login).
"""

StrictAuthenticationDependency = Annotated[Payload, Depends(check_auth(strict=True))]
"""Зависимость для **строгой** проверки аутентификации.

Предназначена для защищенных эндпоинтов, требующих обязательной аутентификации.
"""
