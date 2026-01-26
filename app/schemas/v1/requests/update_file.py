from app.schemas.v1.requests.upload_file import UploadFileRequest


class UpdateFileRequest(UploadFileRequest):
    """Схема запроса на редактирование медиа-файла.

    Используется в качестве представления данных для обновления
    полей файла. Наследуется от `UploadFileRequest`, т.к. имеет
    те же поля, но отличается семантически.

    See Also
    --------
    app.schemas.v1.requests.upload_file.UploadFileRequest
    """
