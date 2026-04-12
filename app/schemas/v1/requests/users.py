from pydantic import BaseModel, Field

from app.core.types import UNSET, Maybe


class PatchProfileRequest(BaseModel):
    """Схема запроса на частичное редактирование профиля пользователя.

    Используется в качестве представления данных для частичного
    обновления полей профиля пользователя. Все поля опциональны -
    передаются только те атрибуты, которые необходимо изменить.

    Attributes
    ----------
    first_name : Maybe[str]
        Реальное имя пользователя. Если не передан - остаётся `UNSET`
        и текущее значение в базе данных не изменяется.
        Временно не обрабатывается.
    avatar_url : Maybe[str]
        URL аватара пользователя. Если не передан - остаётся `UNSET`
        и текущее значение в базе данных не изменяется.
    """

    # first_name: Maybe[str] = Field(
    #     default_factory=lambda: UNSET,
    #     description="Реальное имя пользователя",
    #     examples=["Владислав"],
    # )
    avatar_url: Maybe[str] = Field(
        default_factory=lambda: UNSET,
        description="URL аватара пользователя",
        examples=[
            "https://avatars.githubusercontent.com/u/22058897?s=400&u=46b96191222ac11e6afda1648ad912384d8a8a30&v=4"
        ],
    )
