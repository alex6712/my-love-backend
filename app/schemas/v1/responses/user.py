from pydantic import Field

from app.schemas.dto.users import UserDTO
from app.schemas.v1.responses.standard import StandardResponse


class UserResponse(StandardResponse):
    """Модель ответа сервера с информацией о пользователе.

    Attributes
    ----------
    user : UserDTO | None
        DTO запрашиваемого пользователя, или None если пользователя не найден.
    """

    user: UserDTO | None = Field(
        description="DTO запрашиваемого пользователя, или None если пользователя не найден.",
    )
