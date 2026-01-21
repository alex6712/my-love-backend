from typing import Annotated

from fastapi import APIRouter, Body, Request, Response, status

from app.core.dependencies.auth import (
    AuthServiceDependency,
    ExtractAccessTokenDependency,
    ExtractRefreshTokenDependency,
    SignInCredentialsDependency,
)
from app.core.docs import (
    AUTHORIZATION_ERROR_REF,
    LOGIN_ERROR_REF,
    RATE_LIMIT_ERROR_REF,
    REGISTER_ERROR_REF,
)
from app.core.rate_limiter import LOGIN_LIMIT, REFRESH_LIMIT, REGISTER_LIMIT, limiter
from app.core.types import Tokens
from app.schemas.v1.requests.register import RegisterRequest
from app.schemas.v1.responses.standard import StandardResponse
from app.schemas.v1.responses.tokens import TokensResponse

router: APIRouter = APIRouter(
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
    auth_service: AuthServiceDependency,
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
    auth_service : AuthServiceDependency
        Зависимость сервиса аутентификации.

    Returns
    -------
    StandardResponse
        Ответ с кодом 201 и сообщением об успешной регистрации.
    """
    await auth_service.register(body.username, body.password)

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
    auth_service: AuthServiceDependency,
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
    auth_service : AuthServiceDependency
        Зависимость сервиса аутентификации.

    Returns
    -------
    TokensResponse
        Ответ с вложенными JWT access и refresh токенами.
    """
    tokens: Tokens = await auth_service.login(
        form_data.username,
        form_data.password,
    )

    return TokensResponse(
        detail="Login successful.",
        access_token=tokens["access"],
        refresh_token=tokens["refresh"],
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
    refresh_token: ExtractRefreshTokenDependency,
    auth_service: AuthServiceDependency,
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
    refresh_token : ExtractRefreshTokenDependency
        Зависимость на получение токена обновления из заголовков запроса.
    auth_service : AuthServiceDependency
        Зависимость сервиса аутентификации.

    Returns
    -------
    TokensResponse
        Ответ с вложенными JWT access и refresh токенами.
    """
    tokens: Tokens = await auth_service.refresh(refresh_token)

    return TokensResponse(
        detail="Refresh successful.",
        access_token=tokens["access"],
        refresh_token=tokens["refresh"],
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
    access_token: ExtractAccessTokenDependency,
    auth_service: AuthServiceDependency,
) -> StandardResponse:
    """Завершение текущей сессии пользователя.

    Инвалидирует refresh token пользователя.
    Для выполнения операции требуется валидный access token.

    Parameters
    ----------
    access_token : ExtractAccessTokenDependency
        Access token, извлеченный из заголовков запроса.
    auth_service : AuthServiceDependency
        Зависимость сервиса аутентификации.

    Returns
    -------
    StandardResponse
        Стандартный ответ с сообщением об успешном выходе из системы.

    Notes
    -----
    - Access token должен быть валидным на момент выполнения запроса
    - После выполнения запроса refresh token становится недействительным
    """
    await auth_service.logout(access_token)

    return StandardResponse(detail="User successfully logout.")
