from typing import cast
from uuid import UUID, uuid4

from fastapi import UploadFile
from minio import Minio

from app.config import Settings
from app.core.exceptions.media import (
    MediaNotFoundException,
    UnsupportedFileTypeException,
)
from app.infrastructure.postgresql import UnitOfWork
from app.repositories.media import MediaRepository, MediaType
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO
from app.schemas.dto.media import MediaDTO


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
    add_file(file, title, description, created_by)
        Загрузка файла в приватное хранилище.
    create_album(title, description, cover_url, is_private, created_by)
        Создание нового альбома.
    get_albums(creator_id)
        Получение всех альбомов по UUID создателя.
    get_album(album_id, user_id)
        Получение подробной информации об альбоме по его UUID.
    delete_album(album_id, user_id)
        Удаление альбома по его UUID.
    attach(album_id, media_uuids, user_id)
        Прикрепляет медиа-файлы к альбому.
    """

    def __init__(
        self, unit_of_work: UnitOfWork, minio_client: Minio, settings: Settings
    ):
        super().__init__()

        self._media_repo: MediaRepository = unit_of_work.get_repository(MediaRepository)
        self._minio_client: Minio = minio_client
        self._settings: Settings = settings

    async def upload_file(
        self,
        file: UploadFile,
        title: str | None,
        description: str | None,
        created_by: UUID,
    ) -> None:
        """Загрузка файла в приватное хранилище.

        Принимает файл в виде объекта-обёртки `fastapi.UploadFile`, также
        ожидает дополнительные данные о файле для сохранения записи о файле.

        Генерирует уникальное имя файла, используя `uuid4`, сохраняет содержимое
        файла в бакет MinIO, создаёт в базе данных новую запись о загруженном файле.

        Parameters
        ----------
        file : UploadFile
            Файл к загрузке.
        title : str | None
            Наименование загружаемого файла.
        description : str | None
            Описание загружаемого файла.
        created_by : UUID
            UUID пользователя, загрузившего файл.

        Raises
        ------
        UnsupportedFileTypeException
            Возникает в том случае, если тип переданного файла не поддерживается.
        """
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

    async def get_album(self, album_id: UUID, user_id: UUID) -> AlbumWithItemsDTO:
        """Получение подробной информации об альбоме по его UUID.

        Получает на вход UUID медиа-альбома и UUID текущего пользователя,
        возвращает DTO медиа-альбома с подробным представлением входящих
        в него медиа-файлов.

        Parameters
        ----------
        album_id : UUID
            UUID медиа-альбома к получению.
        user_id : UUID
            UUID текущего пользователя.

        Returns
        -------
        AlbumWithItemsDTO
            Подробный DTO медиа-альбома.

        Raises
        ------
        MediaNotFoundException
            В случае если альбом по переданному UUID не существует или
            текущий пользователь не имеет прав на просмотр этого альбома.
        """
        album: (
            AlbumWithItemsDTO | None
        ) = await self._media_repo.get_album_with_items_by_id(album_id)

        if album is None or album.creator.id != user_id:
            raise MediaNotFoundException(
                detail=f"Album with id={album_id} not found, or you're not this album's creator."
            )

        return album

    async def delete_album(self, album_id: UUID, user_id: UUID) -> None:
        """Удаление альбома по его UUID.

        Получает UUID альбома и UUID пользователя, совершающего действие удаления.
        Если UUID пользователя не совпадает с UUID создателя альбома, завершает
        действие исключением. В ином случае удаляет альбом.

        Parameters
        ----------
        album_id : UUID
            UUID альбома к удалению.
        user_id : UUID
            UUID пользователя, запрашивающего удаление.

        Raises
        ------
        MediaNotFoundException
            Возникает в случае, если альбом с переданным UUID не существует
            или текущий пользователь не является создателем альбома.
        """
        album: AlbumDTO | None = await self._media_repo.get_album_by_id(album_id)

        if album is None or album.creator.id != user_id:
            raise MediaNotFoundException(
                detail=f"Album with id={album_id} not found, or you're not this album's creator."
            )

        await self._media_repo.delete_album_by_id(album_id)

    async def attach(
        self, album_id: UUID, media_uuids: list[UUID], user_id: UUID
    ) -> None:
        """Прикрепляет медиа-файлы к альбому.

        Проверяет:
        1. Существование альбома;
        2. Права пользователя на альбом (должен быть создателем);
        3. Существование всех медиа-файлов;
        4. Права пользователя на медиа-файлы (должен быть создателем).

        Parameters
        ----------
        album_id : UUID
            UUID альбома.
        media_uuids : list[UUID]
            Список UUID медиа-файлов для прикрепления.
        user_id : UUID
            UUID пользователя, выполняющего операцию.

        Raises
        ------
        MediaNotFoundException
            Если альбом не существует или не все медиа-файлы найдены.
        """
        album: AlbumDTO | None = await self._media_repo.get_album_by_id(album_id)

        if album is None or album.creator.id != user_id:
            raise MediaNotFoundException(
                detail=f"Album with id={album_id} not found, or you're not this album's creator."
            )

        if not media_uuids:
            return

        media_files: list[MediaDTO] = await self._media_repo.get_media_by_ids(
            media_uuids, created_by=user_id
        )
        found_media_ids: set[UUID] = {media.id for media in media_files}

        if len(found_media_ids) != len(media_uuids):
            missing_ids: set[UUID] = set(media_uuids) - found_media_ids

            missing_list: str = ", ".join(str(mid) for mid in missing_ids)
            raise MediaNotFoundException(
                detail=(
                    "One or more media files not found or you don't have "
                    f"permission to attach them. Missing IDs: {missing_list}"
                )
            )

        attached_media: set[UUID] = await self._media_repo.get_existing_album_items(
            album_id, media_uuids
        )

        await self._media_repo.attach_media_to_album(
            album_id, list(set(media_uuids) - attached_media)
        )
