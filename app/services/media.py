from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.config import Settings
from app.core.enums import FileStatus, IdempotencyStatus
from app.core.exceptions.base import IdempotencyException
from app.core.exceptions.media import (
    MediaNotFoundException,
    UnsupportedFileTypeException,
    UploadNotCompletedException,
)
from app.infrastructure.postgresql import UnitOfWork
from app.infrastructure.redis import RedisClient
from app.repositories.media import MediaRepository
from app.schemas.dto.album import AlbumDTO, AlbumWithItemsDTO
from app.schemas.dto.file import FileDTO
from app.schemas.dto.idempotency_key import IdempotencyKeyDTO

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


class MediaService:
    """Сервис работы с медиа.

    Реализует бизнес-логику для:
    - Регистрации и получения медиа альбомов;
    - Загрузку и выгрузку различных медиа;
    - Управление медиа внутри и между альбомами;
    - Подтверждение успешной загрузки файлов в хранилище.

    Attributes
    ----------
    _redis_client : RedisClient
        Клиент Redis.
    _s3_client : S3Client
        Асинхронный клиент для операций с файлами в S3 хранилище.
    _settings : Settings
        Настройки приложения.
    _media_repo : MediaRepository
        Репозиторий для операций с медиа в БД.

    Methods
    -------
    upload_file(file, title, description, created_by)
        Загрузка файла в приватное хранилище.
    get_upload_presigned_url(file, title, description, created_by)
        Получение presigned-url для загрузка файла в приватное хранилище.
    confirm_upload(file_id, user_id)
        Подтверждение успешной загрузки файла в объектное хранилище.
    create_album(title, description, cover_url, is_private, created_by)
        Создание нового альбома.
    get_albums(creator_id)
        Получение всех альбомов по UUID создателя.
    get_album(album_id, user_id)
        Получение подробной информации об альбоме по его UUID.
    delete_album(album_id, user_id)
        Удаление альбома по его UUID.
    attach(album_id, files_uuids, user_id)
        Прикрепляет медиа-файлы к альбому.
    """

    _IDEMPOTENCY_KEY_TTL: int = 300
    """Время в секундах, которе живёт ключ идемпотентности."""

    _SUPPORTED_CONTENT_TYPES: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "video/mp4",
        "video/quicktime",
    )
    """Поддерживаемые MIME-типы."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        redis_client: RedisClient,
        s3_client: "S3Client",
        settings: Settings,
    ):
        super().__init__()

        self._redis_client: RedisClient = redis_client
        self._s3_client: "S3Client" = s3_client
        self._settings: Settings = settings

        self._media_repo: MediaRepository = unit_of_work.get_repository(MediaRepository)

    async def _idempotency_gate(
        self, idem_scope: str, user_id: UUID, idempotency_key: UUID
    ) -> tuple[bool, str | None]:
        """Управляет проверкой и захватом ключа идемпотентности.

        Выполняет атомарную попытку захватить ключ идемпотентности в Redis.
        Если ключ уже существует и находится в статусе PROCESSING — вызывает
        исключение. Если запрос уже выполнен (DONE) — возвращает кэшированный
        ответ для повторного вызова.

        Parameters
        ----------
        idem_scope : str
            Область применения ключа идемпотентности (например, 'media_upload').
        user_id : UUID
            UUID пользователя, выполняющего запрос.
        idempotency_key : UUID
            Уникальный ключ идемпотентности от клиента.

        Returns
        -------
        tuple[bool, str | None]
            Кортеж из двух элементов:
            - bool: True если ключ захвачен впервые (новый запрос),
                False если запрос уже обрабатывался или завершён.
            - str | None: Кэшированный ответ предыдущего выполнения
                или None для новых запросов.

        Raises
        ------
        IdempotencyException
            Если запрос с переданным ключом идемпотентности уже находится
            в процессе обработки (статус PROCESSING).
        """
        response: str | None = None

        created: bool = await self._redis_client.acquire_idempotency_key(
            idem_scope, user_id, idempotency_key, MediaService._IDEMPOTENCY_KEY_TTL
        )

        if not created:
            key: IdempotencyKeyDTO = await self._redis_client.get_idempotency_state(
                idem_scope, user_id, idempotency_key
            )

            if key.status == IdempotencyStatus.PROCESSING:
                raise IdempotencyException("Request already in progress.")

            response = key.response

        return created, response

    async def upload_file(
        self,
        file: UploadFile,
        title: str | None,
        description: str | None,
        user_id: UUID,
        idempotency_key: UUID,
    ) -> None:
        """Загрузка файла в приватное хранилище.

        Принимает файл в виде объекта-обёртки `fastapi.UploadFile`, также
        ожидает дополнительные данные о файле для сохранения записи о файле.

        Генерирует уникальное имя файла, используя `uuid4`, сохраняет содержимое
        файла в бакет S3, создаёт в базе данных новую запись о загруженном файле.

        Parameters
        ----------
        file : UploadFile
            Файл к загрузке.
        title : str | None
            Наименование загружаемого файла.
        description : str | None
            Описание загружаемого файла.
        user_id : UUID
            UUID пользователя, загрузившего файл.
        idempotency_key : UUID
            Ключ идемпотентности запроса.

        Raises
        ------
        UnsupportedFileTypeException
            Возникает в том случае, если тип переданного файла не поддерживается.
        """
        idem_scope: str = "media_upload_proxy"

        new, _ = await self._idempotency_gate(idem_scope, user_id, idempotency_key)
        if not new:
            return

        content_type: str | None = file.content_type

        if content_type is None or content_type not in self._SUPPORTED_CONTENT_TYPES:
            raise UnsupportedFileTypeException(
                detail=(
                    f"File type '{content_type}' is not supported. "
                    f"Supported types: {self._SUPPORTED_CONTENT_TYPES}."
                )
            )

        object_key: str = f"uploads/{uuid4().hex}"

        await self._s3_client.upload_fileobj(
            Fileobj=file.file,
            Bucket=self._settings.MINIO_BUCKET_NAME,
            Key=object_key,
            ExtraArgs={"ContentType": content_type},
        )

        self._media_repo.add_file(
            object_key=object_key,
            content_type=content_type,
            title=title,
            description=description,
            created_by=user_id,
        )

        await self._redis_client.finalize_idempotency_key(
            idem_scope, user_id, idempotency_key, self._IDEMPOTENCY_KEY_TTL
        )

    async def get_upload_presigned_url(
        self,
        content_type: str,
        title: str | None,
        description: str | None,
        user_id: UUID,
        idempotency_key: UUID,
    ) -> tuple[UUID, str]:
        """Получение presigned-url для загрузка файла в приватное хранилище.

        Принимает дополнительные данные о файле для сохранения записи о файле.

        Генерирует уникальное имя файла, используя `uuid4`, генерирует presigned-url
        для прямой загрузки в S3 хранилище, создаёт в базе данных новую запись о загруженном файле.

        Parameters
        ----------
        content_type : str
            MIME-тип отправляемого файла.
        title : str | None
            Наименование загружаемого файла.
        description : str | None
            Описание загружаемого файла.
        user_id : UUID
            UUID пользователя, загрузившего файл.
        idempotency_key : UUID
            Ключ идемпотентности запроса.

        Raises
        ------
        UnsupportedFileTypeException
            Возникает в том случае, если тип переданного файла не поддерживается.
        """
        idem_scope: str = "media_upload_direct"

        new, response = await self._idempotency_gate(
            idem_scope, user_id, idempotency_key
        )
        if not new:
            id_, url = response.split(",", 1)  # type: ignore
            return UUID(id_), url

        file_id: UUID = uuid4()

        if content_type not in self._SUPPORTED_CONTENT_TYPES:
            raise UnsupportedFileTypeException(
                detail=(
                    f"File type '{content_type}' is not supported. "
                    f"Supported types: {self._SUPPORTED_CONTENT_TYPES}."
                )
            )

        object_key: str = f"uploads/{uuid4().hex}"

        file_id: UUID = self._media_repo.add_pending_file(
            object_key=object_key,
            content_type=content_type,
            title=title,
            description=description,
            created_by=user_id,
        )

        url: str = await self._s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._settings.MINIO_BUCKET_NAME,
                "Key": object_key,
            },
            ExpiresIn=self._settings.PRESIGNED_URL_EXPIRATION,
        )

        await self._redis_client.finalize_idempotency_key(
            scope=idem_scope,
            user_id=user_id,
            key=idempotency_key,
            ttl=self._IDEMPOTENCY_KEY_TTL,
            response=f"{file_id},{url}",
        )

        return file_id, url

    async def confirm_upload(self, file_id: UUID, user_id: UUID) -> None:
        """Подтверждает успешную загрузку файла в объектное хранилище.

        Проверяет наличие файла в базе данных и его физическое присутствие
        в объектном хранилище (S3/MinIO), после чего обновляет статус файла
        на UPLOADED. Используется при асинхронной загрузке файлов через
        presigned URL.

        Parameters
        ----------
        file_id : UUID
            UUID медиа-файла для подтверждения загрузки.
        user_id : UUID
            UUID пользователя-создателя файла.
            Используется для проверки прав доступа.

        Raises
        ------
        MediaNotFoundException
            Если файл с указанным ID не найден в базе данных или
            текущий пользователь не является создателем файла.
        UploadNotCompletedException
            Если файл не найден в объектном хранилище, то есть
            загрузка не была завершена или файл был удалён.
        """
        files: list[FileDTO] = await self._media_repo.get_files_by_ids(
            [file_id], created_by=user_id
        )

        if len(files) != 1:
            raise MediaNotFoundException(
                media_type="file",
                detail=f"File with id={file_id} not found, or you're not this file's creator.",
            )

        file: FileDTO = files[0]

        if file.status == FileStatus.UPLOADED:
            return

        exists: bool = False
        try:
            await self._s3_client.head_object(
                Bucket=self._settings.MINIO_BUCKET_NAME,
                Key=file.object_key,
            )
            exists = True
        except ClientError:
            pass

        if not exists:
            raise UploadNotCompletedException(
                detail=f"File with id={file_id} not found in object storage.",
            )

        await self._media_repo.mark_file_uploaded(file.id)

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
        self._media_repo.add_album(
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
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're not this album's creator.",
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
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're not this album's creator.",
            )

        await self._media_repo.delete_album_by_id(album_id)

    async def attach(
        self, album_id: UUID, files_uuids: list[UUID], user_id: UUID
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
        files_uuids : list[UUID]
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
                media_type="album",
                detail=f"Album with id={album_id} not found, or you're not this album's creator.",
            )

        if not files_uuids:
            return

        files: list[FileDTO] = await self._media_repo.get_files_by_ids(
            files_uuids, created_by=user_id
        )
        found_files_ids: set[UUID] = {file.id for file in files}

        if len(found_files_ids) != len(files_uuids):
            missing_ids: set[UUID] = set(files_uuids) - found_files_ids

            missing_list: str = ", ".join(str(mid) for mid in missing_ids)
            raise MediaNotFoundException(
                media_type="file",
                detail=(
                    "One or more media files not found or you don't have "
                    f"permission to attach them. Missing IDs: {missing_list}"
                ),
            )

        attached_files: set[UUID] = await self._media_repo.get_existing_album_items(
            album_id, files_uuids
        )

        self._media_repo.attach_files_to_album(
            album_id, list(set(files_uuids) - attached_files)
        )
