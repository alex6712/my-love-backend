from uuid import UUID

from pydantic import BaseModel, Field


class CreateAlbumRequest(BaseModel):
    """Схема запроса на создание медиа-альбома.

    Используется в качестве представления информации о новом альбоме.

    Attributes
    ----------
    title : str
        Наименование альбома.
    description : str | None
        Описание альбома.
    cover_url : str | None
        URL обложки альбома.
    is_private : bool
        Видимость альбома (True - личный или False - публичный).
    """

    title: str = Field(
        default="Новый альбом",
        description="Наименование медиа альбома",
        examples=["Поездка в Париж 2004"],
    )
    description: str | None = Field(
        default=None,
        description="Описание медиа альбома",
        examples=["Альбом с романтичными видами Города Любви!"],
    )
    cover_url: str | None = Field(
        default=None,
        description="Ссылка на обложку медиа альбома",
        examples=[
            "https://camo.githubusercontent.com/78a574a2925825ac33911b5a8bad6176bea158260c4581a72129bfa8d2ce87f3/68747470733a2f2f7777772e6963656769662e636f6d2f77702d636f6e74656e742f75706c6f6164732f323032332f30312f6963656769662d3136322e676966"
        ],
    )
    is_private: bool = Field(
        default=False,
        description="Видимость альбома (True - личный или False - публичный)",
        examples=[True, False],
    )


class PatchAlbumRequest(BaseModel):
    """Схема запроса на частичное редактирование медиа-альбома.

    Используется в качестве представления данных для частичного
    обновления полей альбома. Все поля опциональны — передаются
    только те атрибуты, которые необходимо изменить.

    Attributes
    ----------
    title : str | None
        Наименование альбома. Если передано None, текущее
        значение не изменяется.
    description : str | None
        Описание альбома. Если передано None, текущее
        значение не изменяется.
    cover_url : str | None
        URL обложки альбома. Если передано None, текущее
        значение не изменяется.
    is_private : bool | None
        Видимость альбома (True - личный или False - публичный).
        Если передано None, текущее значение не изменяется.
    """

    title: str | None = Field(
        default=None,
        description="Наименование медиа альбома",
        examples=["Поездка в Париж 2004"],
    )
    description: str | None = Field(
        default=None,
        description="Описание медиа альбома",
        examples=["Альбом с романтичными видами Города Любви!"],
    )
    cover_url: str | None = Field(
        default=None,
        description="Ссылка на обложку медиа альбома",
        examples=[
            "https://camo.githubusercontent.com/78a574a2925825ac33911b5a8bad6176bea158260c4581a72129bfa8d2ce87f3/68747470733a2f2f7777772e6963656769662e636f6d2f77702d636f6e74656e742f75706c6f6164732f323032332f30312f6963656769662d3136322e676966"
        ],
    )
    is_private: bool | None = Field(
        default=None,
        description="Видимость альбома (True - личный или False - публичный)",
        examples=[True, False],
    )


class AttachFilesRequest(BaseModel):
    """Схема запроса на добавления медиа-файлов к альбому.

    Используется в качестве представления информации о списке
    добавляемых в медиа альбом файлов.

    Attributes
    ----------
    files_uuids : list[UUID]
        Список UUID медиа-файлов к добавлению.
    """

    files_uuids: list[UUID] = Field(
        description="Список UUID медиа-файлов, которые необходимо добавить в альбом.",
        examples=[
            [
                "681cbf12-fe3f-41f4-92f1-c8cb33dfe47e",
                "f466bb69-bf31-4125-a29a-35166033e4ef",
            ]
        ],
    )
