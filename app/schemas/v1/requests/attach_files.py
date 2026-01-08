from uuid import UUID

from pydantic import BaseModel, Field


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
