from app.core.types import UNSET, Maybe
from app.schemas.dto.base import BaseCreateDTO, BaseSQLCoreDTO, BaseUpdateDTO


class UserDTO(BaseSQLCoreDTO):
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
    """

    password_hash: str


class CreatorDTO(UserDTO):
    """DTO для представления создателя сущности.

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


class CreateUserDTO(BaseCreateDTO):
    username: str
    password_hash: str


class PatchProfileDTO(BaseUpdateDTO):
    """DTO для частичного обновления профиля пользователя.

    Attributes
    ----------
    first_name : Maybe[str]
        Новое реальное имя пользователя. Если `UNSET` - поле не изменяется.
        Временно не обрабатывается.
    avatar_url : Maybe[str]
        Новый URL аватара пользователя. Если `UNSET` - поле не изменяется.
    """

    # first_name: Maybe[str] = UNSET
    avatar_url: Maybe[str] = UNSET
