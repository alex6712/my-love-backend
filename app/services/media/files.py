from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from botocore.exceptions import ClientError
from fastapi import UploadFile
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
from app.repositories.media import FilesRepository
from app.schemas.dto.file import FileDTO
from app.schemas.dto.idempotency_key import IdempotencyKeyDTO

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
    _file_repo : FilesRepository
        Репозиторий для операций с файлами в БД.

    Methods
    -------
    upload_file(file, title, description, created_by, idempotency_key)
        Загрузка файла в приватное хранилище через прокси.
    get_upload_presigned_url(content_type, title, description, created_by, idempotency_key)
        Получение presigned-url для загрузки файла напрямую в S3.
    confirm_upload(file_id, user_id)
        Подтверждение успешной загрузки файла в объектное хранилище.
    get_download_presigned_url(file_id, user_id)
        Получение presigned-url для получения файла из приватного хранилища.
    """

    _IDEMPOTENCY_KEY_TTL: int = 300
    """Время в секундах, которое живёт ключ идемпотентности."""

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

        self._file_repo: FilesRepository = unit_of_work.get_repository(FilesRepository)

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
            idem_scope, user_id, idempotency_key, FilesService._IDEMPOTENCY_KEY_TTL
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
        """Загрузка файла в приватное хранилище через прокси.

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
        IdempotencyException
            Возникает в том случае, если запрос с переданным ключом идемпотентности
            уже находится в процессе обработки.
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

        self._file_repo.add_file(
            object_key=object_key,
            content_type=content_type,
            title=title,
            description=description,
            created_by=user_id,
        )

        await self._redis_client.finalize_idempotency_key(
            idem_scope, user_id, idempotency_key, FilesService._IDEMPOTENCY_KEY_TTL
        )

    async def get_upload_presigned_url(
        self,
        content_type: str,
        title: str | None,
        description: str | None,
        user_id: UUID,
        idempotency_key: UUID,
    ) -> tuple[UUID, AnyHttpUrl]:
        """Получение presigned-url для загрузки файла напрямую в S3.

        Принимает дополнительные данные о файле для сохранения записи о файле.

        Генерирует уникальное имя файла, используя `uuid4`, генерирует presigned-url
        для прямой загрузки в S3 хранилище, создаёт в базе данных новую запись о загружаемом файле.

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

        Returns
        -------
        tuple[UUID, AnyHttpUrl]
            Кортеж, состоящий из:
            - UUID загружаемого файла;
            - Presigned URL для прямой загрузки в S3.

        Raises
        ------
        UnsupportedFileTypeException
            Возникает в том случае, если тип переданного файла не поддерживается.
        IdempotencyException
            Возникает в том случае, если запрос с переданным ключом идемпотентности
            уже находится в процессе обработки.
        """
        idem_scope: str = "media_upload_direct"

        new, response = await self._idempotency_gate(
            idem_scope, user_id, idempotency_key
        )
        if not new:
            id_, url = response.split(",", 1)  # type: ignore
            return UUID(id_), AnyHttpUrl(url)

        if content_type not in self._SUPPORTED_CONTENT_TYPES:
            raise UnsupportedFileTypeException(
                detail=(
                    f"File type '{content_type}' is not supported. "
                    f"Supported types: {self._SUPPORTED_CONTENT_TYPES}."
                )
            )

        object_key: str = f"uploads/{uuid4().hex}"

        file_id: UUID = self._file_repo.add_pending_file(
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
            ttl=FilesService._IDEMPOTENCY_KEY_TTL,
            response=f"{file_id},{url}",
        )

        return file_id, AnyHttpUrl(url)

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
        files: list[FileDTO] = await self._file_repo.get_files_by_ids(
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
                detail=f"File with id={file_id} has not been found in object storage yet.",
            )

        await self._file_repo.mark_file_uploaded(file.id)

    async def get_download_presigned_url(
        self, file_id: UUID, user_id: UUID
    ) -> tuple[UUID, AnyHttpUrl]:
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
        tuple[UUID, AnyHttpUrl]
            Кортеж, состоящий из:
            - UUID файла;
            - Presigned URL для прямого скачивания.

        Raises
        ------
        MediaNotFoundException
            Файл с переданным UUID не найден или пользователь не имеет прав на его просмотр.
        UploadNotCompletedException
            Возникает в случае, если файл находится в статусе загрузки (PENDING),
            загрузка не удалась (FAILED) или файл был удалён (DELETED).
        """
        files: list[FileDTO] = await self._file_repo.get_files_by_ids(
            [file_id], created_by=user_id
        )

        if len(files) != 1:
            raise MediaNotFoundException(
                media_type="file",
                detail=f"File with id={file_id} not found, or you're not this file's creator.",
            )

        file: FileDTO = files[0]

        match file.status:
            case FileStatus.PENDING:
                raise UploadNotCompletedException(
                    detail=f"File with id={file_id} is now uploading.",
                )
            case FileStatus.FAILED:
                raise UploadNotCompletedException(
                    detail=f"There were an error while uploading file with id={file_id}. File not accessible.",
                )
            case FileStatus.DELETED:
                raise MediaNotFoundException(
                    media_type="file",
                    detail=f"File with id={file_id} has been deleted.",
                )
            case FileStatus.UPLOADED:
                pass

        url: str = await self._s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._settings.MINIO_BUCKET_NAME,
                "Key": file.object_key,
            },
            ExpiresIn=self._settings.PRESIGNED_URL_EXPIRATION,
        )

        return file_id, AnyHttpUrl(url)
