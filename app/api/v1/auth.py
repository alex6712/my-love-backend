from fastapi import APIRouter, status

from app.core.dependencies.auth import (
    AuthServiceDependency,
    ExtractAccessTokenDependency,
    ExtractRefreshTokenDependency,
    SignInCredentialsDependency,
    StrictAuthenticationDependency,
)
from app.core.security import Tokens
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
    summary="Регистрация пользователя",
)
async def register(
    form_data: RegisterRequest,
    auth_service: AuthServiceDependency,
) -> StandardResponse:
    """Регистрация нового пользователя.

    Принимает данные для регистрации (имя пользователя и пароль),
    создает нового пользователя в системе.

    Parameters
    -----------
    form_data : RegisterRequest
        Зависимость для получения данных регистрации из формы.
    auth_service : AuthServiceDependency
        Зависимость сервиса аутентификации.

    Returns
    -------
    StandardResponse
        Ответ с кодом 201 и сообщением об успешной регистрации.
    """
    await auth_service.register(form_data.username, form_data.password)

    return StandardResponse(
        code=status.HTTP_201_CREATED, message="Пользователь успешно зарегистрирован."
    )


@router.post(
    "/login",
    response_model=TokensResponse,
    status_code=status.HTTP_200_OK,
    summary="Аутентификация пользователя и установка токенов в cookies",
)
async def login(
    form_data: SignInCredentialsDependency,
    auth_service: AuthServiceDependency,
) -> TokensResponse:
    """Аутентификация пользователя.

    Принимает учетные данные пользователя, проверяет их и возвращает JWT-токены.

    Parameters
    -----------
    form_data : SignInCredentialsDependency
        Зависимость для получения учетных данных из формы.
    auth_service : AuthServiceDependency
        Зависимость сервиса аутентификации.

    Returns
    -------
    TokensResponse
        Ответ с вложенными JWT.
    """
    tokens: Tokens = await auth_service.login(
        form_data.username,
        form_data.password,
    )

    return TokensResponse(
        access_token=tokens["access"],
        refresh_token=tokens["refresh"],
    )


@router.get(
    "/refresh",
    response_model=TokensResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновление токенов доступа",
)
async def refresh(
    refresh_token: ExtractRefreshTokenDependency,
    auth_service: AuthServiceDependency,
) -> TokensResponse:
    """Обновление пары JWT-токенов.

    Использует refresh token для генерации новой пары токенов.

    Parameters
    ----------
    refresh_token : ExtractRefreshTokenDependency
        Зависимость на получение токена обновления из заголовков запроса.
    auth_service : AuthServiceDependency
        Зависимость сервиса аутентификации.

    Returns
    -------
    TokensResponse
        Ответ с вложенными JWT.
    """
    tokens: Tokens = await auth_service.refresh(refresh_token)

    return TokensResponse(
        access_token=tokens["access"],
        refresh_token=tokens["refresh"],
    )


@router.post(
    "/logout",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Выход из системы",
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

    return StandardResponse(message="User successfully logout.")


@router.get(
    "/verify",
    response_model=StandardResponse,
    status_code=status.HTTP_200_OK,
    summary="Проверка валидности токена доступа",
)
async def verify(_: StrictAuthenticationDependency) -> StandardResponse:
    return StandardResponse(message="Token validation is successful.")
