from typing import Annotated

from fastapi import Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.cookies import get_access_token, get_refresh_token, set_auth_cookies
from app.core.dependencies.services import ServiceManagerDependency
from app.core.dependencies.settings import SettingsDependency
from app.core.exceptions.auth import (
    AuthDomainException,
    InvalidTokenException,
    TokenNotPassedException,
    TokenRevokedException,
    TokenSignatureExpiredException,
)
from app.core.security import jwt_decode
from app.infra.postgres.uow import UnitOfWork
from app.infra.redis import redis_client
from app.schemas.dto.payload import AccessTokenPayload
from app.services.auth import AuthService

SignInCredentialsDependency = Annotated[OAuth2PasswordRequestForm, Depends()]
"""Зависимость на получение реквизитов для входа в систему.

Принимает данные из тела запроса в формате
`application/x-www-form-urlencoded` согласно спецификации
OAuth2 Password Grant (поля `username` и `password`).
"""


async def _resolve_auth(
    request: Request,
    response: Response,
    settings: SettingsDependency,
    services: ServiceManagerDependency,
) -> AccessTokenPayload | None:
    """Разрешает сессию пользователя по auth-cookie.

    На каждый запрос с объявленной auth-зависимостью выполняет:

    1. Чтение access-cookie из запроса. Если токен валиден
       (корректная подпись + отсутствие в Redis blacklist) -
       payload возвращается вызывающему коду.
    2. Если access-cookie отсутствует или его валидация
       завершилась `TokenSignatureExpiredException`,
       `TokenRevokedException` или `InvalidTokenException` -
       выполняется попытка прозрачной ротации пары токенов
       по refresh-cookie. При успехе новые `access` и
       `refresh` токены записываются в исходящий ответ
       через `set_auth_cookies`, а payload нового
       access-токена возвращается вызывающему коду.
    3. Если ни access, ни refresh cookie не позволили
       сформировать валидную сессию, возвращается `None`.

    Parameters
    ----------
    request : Request
        Объект входящего HTTP-запроса.
    response : Response
        Объект HTTP-ответа, через который FastAPI позволяет
        зависимости модифицировать финальный ответ маршрута
        (в данном случае - установить новые `Set-Cookie`
        заголовки после успешной ротации).
    settings : Settings
        Конфигурация приложения, описывающая имена и
        атрибуты auth-cookie.
    services : ServiceManager
        Request-scoped менеджер сервисов, предоставляющий
        доступ к `AuthService` для валидации access-токена.
        Использует общий с маршрутом `UnitOfWork`.

    Returns
    -------
    AccessTokenPayload | None
        Валидированный payload access-токена при его наличии
        либо `None`, если ни access, ни refresh cookie не
        позволили сформировать валидную сессию.

    Notes
    -----
    Ротация refresh-токена выполняется в **изолированном**
    короткоживующем `UnitOfWork`, не разделяемом с маршрутом.
    Это сознательное решение, обеспечивающее коммит обновления
    записи `user_sessions` в БД **до** запуска тела маршрута.
    """
    if (access_token := get_access_token(request, settings)) is not None:
        try:
            return await services.auth.validate_access_token(access_token)
        except (
            TokenSignatureExpiredException,
            TokenRevokedException,
            InvalidTokenException,
        ):
            pass

    return await _try_refresh_session(request, response, settings)


async def _try_refresh_session(
    request: Request, response: Response, settings: SettingsDependency
) -> AccessTokenPayload | None:
    """Пытается прозрачно обновить пару токенов по refresh-cookie.

    Извлекает refresh-cookie из запроса, делегирует ротацию
    `AuthService.rotate_session` в изолированном `UnitOfWork`
    и при успехе устанавливает новые `access`/`refresh` cookie
    в исходящий ответ.

    Parameters
    ----------
    request : Request
        Объект входящего HTTP-запроса, из которого извлекается
        refresh-cookie.
    response : Response
        Объект HTTP-ответа, в который добавляются
        `Set-Cookie` заголовки с обновлённой парой токенов
        при успешной ротации.
    settings : Settings
        Конфигурация приложения, описывающая имена cookie
        и параметры их установки.

    Returns
    -------
    AccessTokenPayload | None
        Payload нового access-токена при успешной ротации
        либо `None`, если refresh-cookie отсутствует,
        невалиден или ротация завершилась доменной ошибкой
        auth-домена.

    Notes
    -----
    Прямое создание `UnitOfWork` и `AuthService` внутри
    функции обусловлено требованием изолированной транзакции
    для ротации. Все остальные auth-сценарии в проекте
    работают через `ServiceManagerDependency`.
    """
    if (refresh_token := get_refresh_token(request, settings)) is None:
        return None

    try:
        async with UnitOfWork() as rotation_uow:
            rotation_service = AuthService(rotation_uow, redis_client, settings)
            new_tokens = await rotation_service.rotate_session(refresh_token)
    except AuthDomainException:
        return None

    set_auth_cookies(
        response,
        access_token=new_tokens.access,
        refresh_token=new_tokens.refresh,
        settings=settings,
    )

    return jwt_decode(new_tokens.access, "access")


SoftAuthenticationDependency = Annotated[
    AccessTokenPayload | None, Depends(_resolve_auth)
]
"""Зависимость для мягкой проверки аутентификации.

Используется в эндпоинтах, доступных как аутентифицированным,
так и неаутентифицированным пользователям.

При отсутствии валидной сессии возвращает `None` -
endpoint сам решает, что с этим делать.
"""


async def _require_auth(payload: SoftAuthenticationDependency) -> AccessTokenPayload:
    """Приводит мягкий результат `_resolve_auth` к строгой форме.

    Используется как обёртка над `SoftAuthenticationDependency`
    для формирования `StrictAuthenticationDependency`.

    Parameters
    ----------
    payload : AccessTokenPayload | None
        Результат `_resolve_auth`. Может быть `None`, если
        валидная сессия не была сформирована ни по access,
        ни по refresh cookie.

    Returns
    -------
    AccessTokenPayload
        Гарантированно непустой payload access-токена.

    Raises
    ------
    TokenNotPassedException
        Если `payload is None` - валидная сессия отсутствует
        (пользователь не аутентифицирован или refresh не
        удался). Приводит к HTTP 401 через зарегистрированный
        exception handler.
    """
    if payload is None:
        raise TokenNotPassedException(
            detail=(
                "Access token not found in auth cookie. Make sure to log in first."
            ),
            token_type="access",
        )

    return payload


StrictAuthenticationDependency = Annotated[AccessTokenPayload, Depends(_require_auth)]
"""Зависимость для строгой проверки аутентификации.

Используется в защищённых эндпоинтах, требующих
обязательной аутентификации. При отсутствии валидной
сессии поднимает `TokenNotPassedException` (HTTP 401).
"""
