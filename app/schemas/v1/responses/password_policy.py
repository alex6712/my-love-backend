from pydantic import Field

from app.schemas.dto.password import PasswordRule
from app.schemas.v1.responses.standard import StandardResponse


class PasswordPolicyResponse(StandardResponse):
    """Модель ответа на запрос политики валидации паролей.

    Атрибуты
    --------
    rules : list[PasswordRule]
        Массив правил валидации паролей. Каждый элемент описывает
        одно требование к паролю.
    version : str
        Версия политики валидации (semver).
    """

    rules: list[PasswordRule] = Field(description="Массив правил валидации паролей")
    version: str = Field(
        default="1.0.0",
        description="Версия политики валидации (semver)",
        examples=["1.0.0"],
    )
