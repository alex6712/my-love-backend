from app.schemas.dto.base import BaseSQLModelDTO


class UserDTO(BaseSQLModelDTO):
    """DTO для представления пользователя системы.

    Attributes
    ----------
    username : str
        Логин пользователя для входа в систему.
    avatar_url : str | None
        URL аватара пользователя.
    is_active : bool
        Статус пользователя (True - активный или False - заблокирован)
    """

    username: str
    avatar_url: str | None
    is_active: bool


class UserWithCredentialsDTO(UserDTO):
    """DTO для представления пользователя системы (с учётными данными).

    Наследуется от `UserDTO` вместе с остальными атрибутами пользователя.
    Является строго внутренним DTO, никогда не передаётся клиенту.

    Attributes
    ----------
    password_hash : str
        Хэш пароля пользователя.
    refresh_token_hash : str | None
        Хэш refresh-токена для управления сессиями.
    """

    password_hash: str
    refresh_token_hash: str | None


class CreatorDTO(UserDTO):
    """DTO для представления создателя медиа.

    Notes
    -----
    Наследуется от `UserDTO`, имеет тот же самый
    набор атрибутов. Выделен в отдельный класс из
    соображений семантики.
    """

    pass


class PartnerDTO(UserDTO):
    """DTO для представления партнёра пользователя.

    Notes
    -----
    Наследуется от `UserDTO`, имеет тот же самый
    набор атрибутов. Выделен в отдельный класс из
    соображений семантики.
    """

    pass
