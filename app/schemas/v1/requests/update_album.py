from app.schemas.v1.requests.create_album import CreateAlbumRequest


class UpdateAlbumRequest(CreateAlbumRequest):
    """Схема запроса на редактирование медиа-альбома.

    Используется в качестве представления данных для обновления
    полей альбома. Наследуется от `CreateAlbumRequest`, т.к. имеет
    те же поля, но отличается семантически.

    See Also
    --------
    app.schemas.v1.requests.create_album.CreateAlbumRequest
    """
