import asyncio
import json
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from botocore.exceptions import ClientError
from pydantic import AnyHttpUrl

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
from app.repositories.couples import CouplesRepository
from app.repositories.media import FilesRepository
from app.schemas.dto.file import FileDTO, FileMetadataDTO
from app.schemas.dto.presigned_url import PresignedURLDTO

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


class FilesService:
    """Сервис работы с медиа-файлами.

    Реализует бизнес-логику для:
    - Загрузки файлов в приватное хранилище;
    - Получения presigned URL для загрузки и скачивания;
    - Подтверждения успешной загрузки файлов в хранилище.

    Attributes
    ----------
    _redis_client : RedisClient
        Клиент Redis для управления ключами идемпотентности.
    _s3_client : S3Client
        Асинхронный клиент для операций с файлами в S3 хранилище.
    _settings : Settings
        Настройки приложения.
    _files_repo : FilesRepository
        Репозиторий для операций с файлами в БД.

    Methods
    -------
    get_files(offset, limit, user_id)
        Получение всех файлов по UUID создателя.
    get_upload_presigned_url(files_metadata, user_id, idempotency_key)
        Получение presigned-url для загрузки файла напрямую в S3.
    get_upload_presigned_urls(files_metadata, user_id, idempotency_key)
        Получение presigned-url для загрузки нескольких файлов напрямую в S3.
    confirm_upload(file_id, user_id)
        Подтверждение успешной загрузки файла в объектное хранилище.
    get_download_presigned_url(file_id, user_id)
        Получение presigned-url для получения файла из приватного хранилища.
    update_file(file_id, title, description, user_id)
        Обновление атрибутов медиа-файла по его UUID.
    delete_file(file_id, user_id)
        Удаление файла по его UUID.
    """

    _IDEMPOTENCY_KEY_TTL = 300
    """Время в секундах, которое живёт ключ идемпотентности."""

    _SUPPORTED_CONTENT_TYPES = (
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

        self._redis_client = redis_client
        self._s3_client = s3_client
        self._settings = settings

        self._couples_repo = unit_of_work.get_repository(CouplesRepository)
        self._files_repo = unit_of_work.get_repository(FilesRepository)

    @staticmethod
    def _generate_object_key(user_id: UUID, batch_id: UUID) -> str:
        """Генерация уникального ключа объекта для хранения в файловом хранилище.

        Создает структурированный ключ, который гарантирует уникальность файлов
        и обеспечивает логическую организацию данных в хранилище.
        Ключ формируется по схеме: `{user_id}/{batch_id}/{уникальный_идентификатор}`.

        Parameters
        ----------
        user_id : UUID
            Уникальный идентификатор пользователя,
            которому принадлежит файл.
        batch_id : UUID
            Уникальный идентификатор пакета (группы файлов).

        Returns
        -------
        str
            Сгенерированный ключ объекта в формате строки.
        """
        return f"{user_id}/{batch_id}/{uuid4().hex}"

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

        created = await self._redis_client.acquire_idempotency_key(
            idem_scope, user_id, idempotency_key, FilesService._IDEMPOTENCY_KEY_TTL
        )

        if not created:
            key = await self._redis_client.get_idempotency_state(
                idem_scope, user_id, idempotency_key
            )

            if key.status == IdempotencyStatus.PROCESSING:
                raise IdempotencyException("Request already in progress.")

            response = key.response

        return created, response

    async def get_files(
        self, offset: int, limit: int, user_id: UUID
    ) -> tuple[list[FileDTO], int]:
        """Получение всех файлов по UUID создателя.

        Получает на вход UUID пользователя, ищет UUID партнёра,
        возвращает список всех файлов, которые доступны пользователю (
        созданы им или его партнёром).

        Parameters
        ----------
        offset : int
            Смещение от начала списка (количество пропускаемых файлов).
        limit : int
            Количество возвращаемых файлов.
        user_id : UUID
            UUID пользователя.

        Returns
        -------
        tuple[list[FileDTO], int]
            Кортеж из списка файлов и общего количества.
        """
        partner_id = await self._couples_repo.get_partner_id_by_user_id(user_id)

        return await self._files_repo.get_files_by_creator(
            offset, limit, user_id, partner_id
        )

    async def get_upload_presigned_url(
        self,
        file_metadata: FileMetadataDTO,
        user_id: UUID,
        idempotency_key: UUID,
    ) -> PresignedURLDTO:
        """Получение presigned-url для загрузки файла напрямую в S3.

        Принимает дополнительные данные о файле для сохранения записи.

        Генерирует уникальный ключ объекта, генерирует presigned-url
        для прямой загрузки в S3 хранилище, создаёт в базе данных новую запись о загружаемом файле.

        Parameters
        ----------
        file_metadata : FileMetadataDTO
            Метаданные загружаемого файла.
        user_id : UUID
            UUID пользователя, загружающего файл.
        idempotency_key : UUID
            Ключ идемпотентности запроса.

        Returns
        -------
        PresignedURLDTO
            Сгенерированная presigned URL.

        Raises
        ------
        UnsupportedFileTypeException
            Возникает в том случае, если тип переданного файла не поддерживается.
        IdempotencyException
            Возникает в том случае, если запрос с переданным ключом идемпотентности
            уже находится в процессе обработки.
        """
        result = await self.get_upload_presigned_urls(
            [file_metadata], user_id, idempotency_key
        )

        return result[0]

    async def get_upload_presigned_urls(
        self,
        files_metadata: list[FileMetadataDTO],
        user_id: UUID,
        idempotency_key: UUID,
    ) -> list[PresignedURLDTO]:
        """Получение presigned-url для загрузки нескольких файлов напрямую в S3.

        Принимает дополнительные данные о файлах для сохранения записи.

        Генерирует уникальные ключи объектов, генерирует presigned-url
        для прямой загрузки в S3 хранилище, создаёт в базе данных новые записи о загружаемых файлах.

        Parameters
        ----------
        files_metadata : list[FileMetadataDTO]
            Список метаданных загружаемых файлов.
        user_id : UUID
            UUID пользователя, загружающего файлы.
        idempotency_key : UUID
            Ключ идемпотентности запроса.

        Returns
        -------
        list[PresignedURLDTO]
            Список сгенерированных presigned URLs.

        Raises
        ------
        UnsupportedFileTypeException
            Возникает в том случае, если тип хотя бы одного из переданных файлов не поддерживается.
        IdempotencyException
            Возникает в том случае, если запрос с переданным ключом идемпотентности
            уже находится в процессе обработки.
        """
        idem_scope = "media_upload_direct"

        new, response = await self._idempotency_gate(
            idem_scope, user_id, idempotency_key
        )
        if not new:
            raws = json.loads(response)  # type: ignore
            return [PresignedURLDTO.model_validate_json(raw) for raw in raws]

        unsupported_types = {
            m.content_type
            for m in files_metadata
            if m.content_type not in FilesService._SUPPORTED_CONTENT_TYPES
        }

        if unsupported_types:
            raise UnsupportedFileTypeException(
                detail=(
                    f"File types '{unsupported_types}' is not supported. "
                    f"Supported types: {FilesService._SUPPORTED_CONTENT_TYPES}."
                )
            )

        object_keys = [
            self._generate_object_key(user_id, idempotency_key)
            for _ in range(len(files_metadata))
        ]

        file_ids = await self._files_repo.add_pending_files(
            files_metadata, object_keys, user_id
        )

        tasks = [
            self._s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._settings.MINIO_BUCKET_NAME,
                    "Key": key,
                },
                ExpiresIn=self._settings.PRESIGNED_URL_EXPIRATION,
            )
            for key in object_keys
        ]
        urls = await asyncio.gather(*tasks)

        result = [
            PresignedURLDTO(file_id=id_, presigned_url=AnyHttpUrl(url))
            for id_, url in zip(file_ids, urls, strict=True)
        ]

        await self._redis_client.finalize_idempotency_key(
            scope=idem_scope,
            user_id=user_id,
            key=idempotency_key,
            ttl=FilesService._IDEMPOTENCY_KEY_TTL,
            response=json.dumps([r.model_dump_json() for r in result]),
        )

        return result

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
        files = await self._files_repo.get_files_by_ids([file_id], user_id)

        if len(files) != 1:
            raise MediaNotFoundException(
                media_type="file",
                detail=f"File with id={file_id} not found, or you're not this file's creator.",
            )

        file = files[0]

        if file.status == FileStatus.UPLOADED:
            return

        exists = False
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
                detail=f"File with id={file_id} has not been found in object storage yet.",
            )

        await self._files_repo.mark_file_uploaded(file.id)

    async def get_download_presigned_url(
        self, file_id: UUID, user_id: UUID
    ) -> PresignedURLDTO:
        """Получение presigned-url для получения файла из приватного хранилища.

        Принимает UUID файла, ищет запись о файле в базе данных, проверяет права доступа
        пользователя к файлу и возвращает Presigned URL.

        Parameters
        ----------
        file_id : UUID
            UUID файла для скачивания на клиент.
        user_id : UUID
            UUID пользователя, запросившего скачивание файла.

        Returns
        -------
        PresignedURLDTO
            Сгенерированная presigned URL.

        Raises
        ------
        MediaNotFoundException
            Файл с переданным UUID не найден или пользователь не имеет прав на его просмотр.
        UploadNotCompletedException
            Возникает в случае, если файл находится в статусе загрузки (PENDING),
            загрузка не удалась (FAILED) или файл был удалён (DELETED).
        """
        result = await self.get_download_presigned_urls([file_id], user_id)

        return result[0]

    async def get_download_presigned_urls(
        self, files_uuids: list[UUID], user_id: UUID
    ) -> list[PresignedURLDTO]:
        """Получение presigned-url для скачивания нескольких файлов напрямую из S3.

        Принимает UUID файлов, ищет записи о файлах в базе данных, проверяет права доступа
        пользователя к файлам и возвращает Presigned URLs.

        Parameters
        ----------
        files_uuids : list[UUID]
            Список метаданных загружаемых файлов.
        user_id : UUID
            UUID пользователя, загружающего файлы.

        Returns
        -------
        list[PresignedURLDTO]
            Список сгенерированных presigned URLs.

        Raises
        ------
        MediaNotFoundException
            Файл с переданным UUID не найден или пользователь не имеет прав на его просмотр.
        UploadNotCompletedException
            Возникает в случае, если файл находится в статусе загрузки (PENDING),
            загрузка не удалась (FAILED) или файл был удалён (DELETED).
        """
        partner_id = await self._couples_repo.get_partner_id_by_user_id(user_id)

        files = await self._files_repo.get_files_by_ids(
            files_uuids, user_id, partner_id
        )

        if len(files) != len(files_uuids):
            missing = set(files_uuids) - {file.id for file in files}

            raise MediaNotFoundException(
                media_type="file",
                detail=f"Files with id in {missing} not found, or you're not this files' creator.",
            )

        for file in files:
            match file.status:
                case FileStatus.PENDING:
                    raise UploadNotCompletedException(
                        detail=f"File with id={file.id} is now uploading.",
                    )
                case FileStatus.FAILED:
                    raise UploadNotCompletedException(
                        detail=f"There were an error while uploading file with id={file.id}. File not accessible.",
                    )
                case FileStatus.DELETED:
                    raise MediaNotFoundException(
                        media_type="file",
                        detail=f"File with id={file.id} has been deleted.",
                    )
                case FileStatus.UPLOADED:
                    continue

        tasks = [
            self._s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._settings.MINIO_BUCKET_NAME,
                    "Key": file.object_key,
                },
                ExpiresIn=self._settings.PRESIGNED_URL_EXPIRATION,
            )
            for file in files
        ]
        urls = await asyncio.gather(*tasks)

        return [
            PresignedURLDTO(file_id=id_, presigned_url=AnyHttpUrl(url))
            for id_, url in zip(files_uuids, urls, strict=True)
        ]

    async def update_file(
        self, file_id: UUID, title: str | None, description: str | None, user_id: UUID
    ) -> None:
        """Обновление атрибутов медиа-файла по его UUID.

        Получает идентификатор партнера текущего пользователя и передает данные
        в репозиторий для обновления файла с учетом прав доступа.

        Parameters
        ----------
        album_id : UUID
            UUID файла к изменению.
        title : str | None
            Новый заголовок файла.
        description : str | None
            Новое описание файла или None для сохранения текущего значения.
        user_id : UUID
            UUID пользователя, инициирующего изменение файла.
        """
        file = await self._files_repo.get_file_by_id(file_id, user_id)

        if file is None:
            raise MediaNotFoundException(
                media_type="file",
                detail=f"File with id={file_id} not found, or you're not this file's creator.",
            )

        if title is None:
            title = file.title
        if description is None:
            description = file.description

        await self._files_repo.update_file_by_id(file_id, title, description)

    async def delete_file(self, file_id: UUID, user_id: UUID) -> None:
        """Удаление файла по его UUID.

        Получает UUID медиа-файла и UUID пользователя, совершающего действие удаления.
        Если UUID пользователя не совпадает с UUID создателя файла, завершает
        действие исключением. В ином случае удаляет файл.

        Parameters
        ----------
        file_id : UUID
            UUID файла к удалению.
        user_id : UUID
            UUID пользователя, запрашивающего удаление.

        Raises
        ------
        MediaNotFoundException
            Возникает в случае, если файл с переданным UUID не существует
            или текущий пользователь не является создателем файла.
        """
        files = await self._files_repo.get_files_by_ids([file_id], user_id)

        if len(files) != 1:
            raise MediaNotFoundException(
                media_type="file",
                detail=f"File with id={file_id} not found, or you're not this file's creator.",
            )

        try:
            await self._s3_client.delete_object(
                Bucket=self._settings.MINIO_BUCKET_NAME,
                Key=files[0].object_key,
            )
        except ClientError:
            pass

        await self._files_repo.delete_file_by_id(file_id)
