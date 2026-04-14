from typing import Annotated

from fastapi import APIRouter, Body, Request, Response, status

from app.core.dependencies.auth import (
    ExtractRefreshTokenDependency,
    SignInCredentialsDependency,
    StrictAuthenticationDependency,
)
from app.core.dependencies.services import ServiceManagerDependency
from app.core.docs import (
    AUTHORIZATION_ERROR_REF,
    CHANGE_PASSWORD_ERROR_REF,
    CHANGE_PASSWORD_VALIDATION_ERROR_REF,
    LOGIN_ERROR_REF,
    RATE_LIMIT_ERROR_REF,
    REGISTER_ERROR_REF,
)
from app.core.rate_limiter import (
    CHANGE_PASSWORD_LIMIT,
    LOGIN_LIMIT,
    REFRESH_LIMIT,
    REGISTER_LIMIT,
    limiter,
)
from app.schemas.v1.requests.auth import ChangePasswordRequest, RegisterRequest
from app.schemas.v1.responses.standard import StandardResponse
from app.schemas.v1.responses.tokens import TokensResponse

router = APIRouter(
    prefix="/auth",
    tags=["authorization"],
)


@router.post(
    "/register",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя.",
    response_description="Успешная регистрация",
    responses={422: REGISTER_ERROR_REF, 429: RATE_LIMIT_ERROR_REF},
)
@limiter.limit(REGISTER_LIMIT)  # type: ignore
async def register(
    request: Request,
    response: Response,
    body: Annotated[
        RegisterRequest, Body(description="Схема запроса на регистрацию пользователя.")
    ],
    services: ServiceManagerDependency,
) -> StandardResponse:
    """Регистрация нового пользователя.

    Принимает данные для регистрации (имя пользователя и пароль),
    создает нового пользователя в системе.

    Parameters
    ----------
    request : Request
        Объект HTTP-запроса. Требуется для работы slowapi.Limiter
        при определении rate limit по IP-адресу клиента.
    response : Response
        Объект HTTP-ответа. Требуется для работы slowapi.Limiter
        при инъекции заголовков X-RateLimit-*.
    body : RegisterRequest
        Данные, полученные от клиента в теле запроса.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.

    Returns
    -------
    StandardResponse
        Ответ с кодом 201 и сообщением об успешной регистрации.
    """
    await services.auth.register(body.username, body.password)

    return StandardResponse(detail="User created successfully.")


@router.post(
    "/login",
    response_model=TokensResponse,
    status_code=status.HTTP_200_OK,
    summary="Аутентификация пользователя.",
    response_description="Успешная аутентификация",
    responses={401: LOGIN_ERROR_REF, 429: RATE_LIMIT_ERROR_REF},
)
@limiter.limit(LOGIN_LIMIT)  # type: ignore
async def login(
    request: Request,
    response: Response,
    form_data: SignInCredentialsDependency,
    services: ServiceManagerDependency,
) -> TokensResponse:
    """Аутентификация пользователя.

    Принимает учетные данные пользователя, проверяет их и возвращает JWT-токены.

    Parameters
    ----------
    request : Request
        Объект HTTP-запроса. Требуется для работы slowapi.Limiter
        при определении rate limit по IP-адресу клиента.
    response : Response
        Объект HTTP-ответа. Требуется для работы slowapi.Limiter
        при инъекции заголовков X-RateLimit-*.
    form_data : SignInCredentialsDependency
        Зависимость для получения учетных данных из формы.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.

    Returns
    -------
    TokensResponse
        Ответ с вложенными JWT access и refresh токенами.
    """
    tokens = await services.auth.login(
        form_data.username,
        form_data.password,
    )

    return TokensResponse(
        detail="Login successful.",
        access_token=tokens.access,
        refresh_token=tokens.refresh,
    )


@router.post(
    "/refresh",
    response_model=TokensResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновление токенов доступа.",
    response_description="Обновление токенов прошло успешно",
    responses={401: AUTHORIZATION_ERROR_REF, 429: RATE_LIMIT_ERROR_REF},
)
@limiter.limit(REFRESH_LIMIT)  # type: ignore
async def refresh(
    request: Request,
    response: Response,
    services: ServiceManagerDependency,
    refresh_token: ExtractRefreshTokenDependency,
) -> TokensResponse:
    """Обновление пары JWT-токенов.

    Использует refresh token для генерации новой пары токенов.
    При успешном обновлении старый refresh token инвалидируется.

    Parameters
    ----------
    request : Request
        Объект HTTP-запроса. Требуется для работы slowapi.Limiter
        при определении rate limit по IP-адресу клиента.
    response : Response
        Объект HTTP-ответа. Требуется для работы slowapi.Limiter
        при инъекции заголовков X-RateLimit-*.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    refresh_token : ExtractRefreshTokenDependency
        Зависимость на получение токена обновления из заголовков запроса.

    Returns
    -------
    TokensResponse
        Ответ с вложенными JWT access и refresh токенами.
    """
    tokens = await services.auth.refresh(refresh_token)

    return TokensResponse(
        detail="Refresh successful.",
        access_token=tokens.access,
        refresh_token=tokens.refresh,
    )


@router.post(
    "/logout",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Выход из системы.",
    response_description="Успешный выход из системы",
    responses={401: AUTHORIZATION_ERROR_REF},
)
async def logout(
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Завершение текущей сессии пользователя.

    Инвалидирует refresh token пользователя.
    Для выполнения операции требуется валидный access token.

    Parameters
    ----------
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Стандартный ответ с сообщением об успешном выходе из системы.

    Notes
    -----
    - Access token должен быть валидным на момент выполнения запроса
    - После выполнения запроса refresh token становится недействительным
    """
    await services.auth.logout(payload)

    return StandardResponse(detail="User successfully logout.")


@router.post(
    "/change-password",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Смена пароля пользователя.",
    response_description="Пароль пользователя изменён успешно",
    responses={
        400: CHANGE_PASSWORD_ERROR_REF,
        401: AUTHORIZATION_ERROR_REF,
        422: CHANGE_PASSWORD_VALIDATION_ERROR_REF,
        429: RATE_LIMIT_ERROR_REF,
    },
)
@limiter.limit(CHANGE_PASSWORD_LIMIT)  # type: ignore
async def change_password(
    request: Request,
    response: Response,
    body: Annotated[
        ChangePasswordRequest,
        Body(description="Схема запроса на изменение пароля пользователя."),
    ],
    services: ServiceManagerDependency,
    payload: StrictAuthenticationDependency,
) -> StandardResponse:
    """Смена пароля текущего пользователя.

    Валидирует текущий пароль и заменяет его на новый.
    Требует наличия действующего access token в заголовках запроса.

    Parameters
    ----------
    request : Request
        Объект HTTP-запроса. Требуется для работы slowapi.Limiter
        при определении rate limit по IP-адресу клиента.
    response : Response
        Объект HTTP-ответа. Требуется для работы slowapi.Limiter
        при инъекции заголовков X-RateLimit-*.
    body : ChangePasswordRequest
        Тело запроса, содержащее текущий и новый пароли пользователя.
    services : ServiceManager
        Менеджер сервисов уровня запроса (request-scoped).

        Предоставляет доступ к бизнес-сервисам приложения
        (например, auth, user, note, file и др.) через единый
        контейнер зависимостей.
    payload : AccessTokenPayload
        Полезная нагрузка (payload) токена доступа.
        Получена автоматически из зависимости на строгую аутентификацию.

    Returns
    -------
    StandardResponse
        Стандартный ответ с подтверждением успешной смены пароля.
    """
    await services.auth.change_password(
        body.current_password, body.new_password, payload
    )

    return StandardResponse(detail="User's password successfully changed.")
