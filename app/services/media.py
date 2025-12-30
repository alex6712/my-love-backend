from typing import cast
from uuid import UUID, uuid4

from fastapi import UploadFile
from minio import Minio

from app.config import Settings
from app.core.exceptions.media import UnsupportedFileTypeException
from app.infrastructure.postgresql import UnitOfWork
from app.repositories.media import MediaRepository, MediaType
from app.schemas.dto.album import AlbumDTO


class MediaService:
    """Сервис работы с медиа.

    Реализует бизнес-логику для:
    - Регистрации и получения медиа альбомов;
    - Загрузку и выгрузку различных медиа;
    - Управление медиа внутри и между альбомами.

    Attributes
    ----------
    _media_repo : MediaRepository
        Репозиторий для операций с медиа в БД.
    _minio_client : Minio
        Клиент для операций с файлами в S3 хранилище.

    Methods
    -------
    create_album(title, description, cover_url, is_private, created_by)
        Создание нового альбома.
    get_albums(creator_id)
        Получение всех альбомов по UUID создателя.
    """

    def __init__(
        self, unit_of_work: UnitOfWork, minio_client: Minio, settings: Settings
    ):
        super().__init__()

        self._media_repo: MediaRepository = unit_of_work.get_repository(MediaRepository)
        self._minio_client: Minio = minio_client
        self._settings: Settings = settings

    async def create_album(
        self,
        title: str,
        description: str | None,
        cover_url: str | None,
        is_private: bool,
        created_by: UUID,
    ) -> None:
        """Создание нового альбома.

        Создаёт новый альбом по переданным данным.

        Parameters
        ----------
        title : str
            Наименование альбома.
        description : str | None
            Описание альбома.
        cover_url : str | None
            URL обложки альбома.
        is_private : bool
            Видимость альбома:
            - True - личный альбом;
            - False - публичный альбом (значение по умолчанию).
        created_by : UUID
            UUID пользователя, создавшего альбом.
        """
        await self._media_repo.add_album(
            title, description, cover_url, is_private, created_by
        )

    async def get_albums(self, creator_id: UUID) -> list[AlbumDTO]:
        """Получение всех альбомов по UUID создателя.

        Получает на вход UUID пользователя, возвращает список
        всех альбомов, для которых данный пользователь считается
        создателем.

        Parameters
        ----------
        creator_id : UUID
            UUID пользователя.

        Returns
        -------
        list[AlbumDTO]
            Список альбомов пользователя.
        """
        return await self._media_repo.get_albums_by_creator_id(creator_id)

    async def upload_file(
        self,
        file: UploadFile,
        title: str | None,
        description: str | None,
        created_by: UUID,
    ) -> None:
        """TODO: Документация, сохранение информации о загруженном файле в базу данных."""
        file.file.seek(0, 2)
        file_size: int = file.file.tell()
        file.file.seek(0)

        supported_types: tuple[str, ...] = (
            "image/jpeg",
            "image/png",
            "video/mp4",
            "video/quicktime",
        )

        if file.content_type not in supported_types:
            raise UnsupportedFileTypeException(
                detail=f"File type '{file.content_type}' is not supported {str(supported_types)}."
            )

        filename: str = uuid4().hex
        file_extension: str = ""

        if file.filename is not None and file.filename.find(".") != -1:
            file_extension = file.filename.rsplit(".")[0]

        if file_extension not in ("jfif", "jpeg", "jpg", "png", "mp4"):
            file_extension = file.content_type.split("/")[1]

        file_path: str = f"uploads/{filename}.{file_extension}"

        try:
            _ = self._minio_client.put_object(
                "my-love-bucket",
                file_path,
                data=file.file,
                length=file_size,
                content_type=file.content_type,
            )
        except Exception:
            raise

        await self._media_repo.add_file(
            url=f"http://{self._settings.MINIO_ENDPOINT}/{file_path}",
            type_=cast(MediaType, file.content_type.split("/")[0]),
            title=title,
            description=description,
            created_by=created_by,
        )
