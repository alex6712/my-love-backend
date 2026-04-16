import asyncio
import json
from typing import TYPE_CHECKING, Literal, overload
from uuid import UUID, uuid4

from botocore.exceptions import ClientError
from pydantic import AnyHttpUrl

from app.config import Settings
from app.core.enums import (
    DownloadFileErrorCode,
    FileStatus,
    IdempotencyStatus,
    SortOrder,
    UploadFileErrorCode,
)
from app.core.exceptions.base import (
    IdempotencyException,
    NothingToUpdateException,
    UnexpectedStateException,
)
from app.core.exceptions.media import (
    FileDeletedException,
    FileInvalidStatusException,
    FilePresignedUrlGenerationFailedException,
    FileUploadFailedException,
    FileUploadPendingException,
    MediaDomainException,
    MediaNotFoundException,
    UnsupportedFileTypeException,
    UploadNotCompletedException,
)
from app.infrastructure.postgresql.uow import UnitOfWork
from app.infrastructure.redis import RedisClient
from app.repositories.couple import CoupleRepository
from app.repositories.media import FileRepository
from app.schemas.dto.file import (
    DownloadFileErrorDTO,
    FileDTO,
    FileMetadataDTO,
    PatchFileDTO,
    UploadFileErrorDTO,
)
from app.schemas.dto.presigned_url import PresignedURLDTO, PresignedURLWithRefDTO

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client

type UploadFilesResult = tuple[list[PresignedURLWithRefDTO], list[UploadFileErrorDTO]]
"""Тип результата операции пакетной выгрузки файлов.

Представляет собой кортеж из двух списков:
- список успешно обработанных файлов с предварительно подписанными URL и обратными ссылками для корреляции;
- список ошибок, возникших при выгрузке соответствующих файлов.

Notes
-----
Используется для возврата результатов batch-операции загрузки файлов на сервер.
"""

type DownloadFilesResult = tuple[list[PresignedURLDTO], list[DownloadFileErrorDTO]]
"""Тип результата операции пакетного скачивания файлов.

Представляет собой кортеж из двух списков:
- список успешно сгенерированных предварительно подписанных URL для скачивания файлов;
- список ошибок, возникших при попытке получить URL для соответствующих файлов.

Notes
-----
Используется для возврата результатов batch-операции получения ссылок на скачивание.
"""


class FileService:
    """Сервис работы с медиа-файлами.

    Реализует бизнес-логику для:
    - Загрузки файлов в приватное хранилище;
    - Получения presigned URL для загрузки и скачивания;
    - Подтверждения успешной загрузки файлов в хранилище.

    Attributes
    ----------
    _redis_client : RedisClient
        Клиент Redis для управления ключами идемпотентности и кэширования запросов.
    _s3_client : S3Client
        Асинхронный клиент для операций с файлами в S3 хранилище.
    _settings : Settings
        Настройки приложения.
    _couple_repo : CoupleRepository
        Репозиторий для операций с парами пользователей в БД.
    _file_repo : FileRepository
        Репозиторий для операций с файлами в БД.

    Methods
    -------
    get_files(offset, limit, user_id)
        Получение всех файлов по UUID создателя.
    count_files(user_id)
        Получение количества всех доступных пользователю медиа-файлов.
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

    _COUNT_CACHE_TTL = 3600
    """Время в секундах, которое живёт кэш счётчика записей."""

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
        self._redis_client = redis_client
        self._s3_client = s3_client
        self._settings = settings

        self._couple_repo = unit_of_work.get_repository(CoupleRepository)
        self._file_repo = unit_of_work.get_repository(FileRepository)

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

    @overload
    async def _idempotency_gate(
        self,
        idem_scope: str,
        user_id: UUID,
        idempotency_key: UUID,
        *,
        not_null: Literal[True],
    ) -> tuple[bool, str]: ...

    @overload
    async def _idempotency_gate(
        self,
        idem_scope: str,
        user_id: UUID,
        idempotency_key: UUID,
        *,
        not_null: Literal[False] = ...,
    ) -> tuple[bool, str | None]: ...

    async def _idempotency_gate(
        self,
        idem_scope: str,
        user_id: UUID,
        idempotency_key: UUID,
        *,
        not_null: bool = False,
    ) -> tuple[bool, str | None]:
        """Управляет проверкой и захватом ключа идемпотентности.

        Выполняет атомарную попытку захватить ключ идемпотентности в Redis.
        Если ключ уже существует и находится в статусе PROCESSING - вызывает
        исключение. Если запрос уже выполнен (DONE) - возвращает кэшированный
        ответ для повторного вызова.

        Parameters
        ----------
        idem_scope : str
            Область применения ключа идемпотентности (например, 'media_upload').
        user_id : UUID
            UUID пользователя, выполняющего запрос.
        idempotency_key : UUID
            Уникальный ключ идемпотентности от клиента.
        not_null : bool, optional
            Если True - гарантирует, что кэшированный ответ не равен None
            для уже обработанных запросов (created=False). При нарушении
            вызывает UnexpectedStateException. По умолчанию False.

        Returns
        -------
        tuple[bool, str]
            Если not_null=True: кэшированный ответ гарантированно str.
        tuple[bool, str | None]
            Если not_null=False (по умолчанию): кэшированный ответ может
            быть None для уже обработанных запросов (created=False).

        В обоих случаях bool-элемент кортежа означает:
            - True  - ключ захвачен впервые, запрос новый.
            - False - запрос уже обрабатывается или завершён.

        Raises
        ------
        IdempotencyException
            Если запрос с переданным ключом идемпотентности уже находится
            в процессе обработки (статус PROCESSING).
        UnexpectedStateException
            Если not_null=True и запрос уже завершён (created=False),
            но кэшированный ответ оказался None - неконсистентное состояние
            в Redis.
        """
        response: str | None = None

        created = await self._redis_client.acquire_idempotency_key(
            idem_scope, user_id, idempotency_key, self._IDEMPOTENCY_KEY_TTL
        )

        if not created:
            key = await self._redis_client.get_idempotency_state(
                idem_scope, user_id, idempotency_key
            )

            if key.status == IdempotencyStatus.PROCESSING:
                raise IdempotencyException("Request already in progress.")

            response = key.response

        if not created and not_null and response is None:
            raise UnexpectedStateException(
                domain="application",
                detail="Unexpected None value for not-null redis cache.",
            )

        return created, response

    def _serialize_idempotency_response(
        self, successful: list[PresignedURLWithRefDTO], failed: list[UploadFileErrorDTO]
    ) -> str:
        """Сериализует результат операции в JSON-строку для сохранения в кэше идемпотентности.

        Формирует структуру с двумя ключами: successful и failed,
        каждый из которых содержит список JSON-сериализованных DTO.
        Используется перед вызовом finalize_idempotency_key.

        Parameters
        ----------
        successful : list[PresignedURLWithRefDTO]
            Список успешно сгенерированных presigned URLs.
        failed : list[UploadFileErrorDTO]
            Список ошибок для файлов, которые не удалось обработать.

        Returns
        -------
        str
            JSON-строка вида:
            {"successful": ["<json>", ...], "failed": ["<json>", ...]}.
        """
        return json.dumps(
            {
                "successful": [url.model_dump_json() for url in successful],
                "failed": [err.model_dump_json() for err in failed],
            }
        )

    async def get_files(
        self, offset: int, limit: int, order: SortOrder, user_id: UUID
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
        order : SortOrder
            Направление сортировки файлов.
        user_id : UUID
            UUID пользователя.

        Returns
        -------
        tuple[list[FileDTO], int]
            Кортеж из списка файлов и общего количества.
        """
        partner_id = await self._couple_repo.get_partner_id_by_user_id(user_id)

        return await self._file_repo.get_files_by_creator(
            offset, limit, order, user_id, partner_id
        )

    async def count_files(self, user_id: UUID) -> int:
        """Получение количества всех доступных пользователю медиа-файлов.

        Возвращает закэшированное значение из Redis, если оно есть.
        В случае cache miss обращается к БД и прогревает кэш.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя.

        Returns
        -------
        int
            Количество доступных пользователю медиа-файлов.
        """
        cached = await self._redis_client.get_count("files", user_id)

        if cached is not None:
            return cached

        partner_id = await self._couple_repo.get_partner_id_by_user_id(user_id)
        count = await self._file_repo.count_files_by_creator(user_id, partner_id)

        await self._redis_client.set_count(
            "files", user_id, count, self._COUNT_CACHE_TTL
        )

        return count

    async def get_upload_presigned_url(
        self,
        file_metadata: FileMetadataDTO,
        user_id: UUID,
        idempotency_key: UUID,
    ) -> PresignedURLWithRefDTO:
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
        PresignedURLWithRefDTO
            Сгенерированная presigned URL и идентификатор созданной записи файла.

        Raises
        ------
        UnsupportedFileTypeException
            Если тип переданного файла не входит в список поддерживаемых.
        IdempotencyException
            Если запрос с переданным ключом идемпотентности уже находится в процессе обработки.
        FilePresignedUrlGenerationFailedException
            Если не удалось сгенерировать presigned URL на стороне S3.
        """
        idem_scope = "media_upload_single_direct"

        is_new, cached = await self._idempotency_gate(
            idem_scope, user_id, idempotency_key, not_null=True
        )
        if not is_new:
            raws = json.loads(cached)
            return PresignedURLWithRefDTO.model_validate_json(raws["successful"][0])

        validated_file = self._validate_file_for_upload(file_metadata)

        object_key = self._generate_object_key(user_id, uuid4())
        file_id = await self._file_repo.add_pending_file(
            validated_file, object_key, user_id
        )

        try:
            url = await self._s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._settings.MINIO_BUCKET_NAME,
                    "Key": object_key,
                },
                ExpiresIn=self._settings.PRESIGNED_URL_EXPIRATION,
            )
        except Exception as exc:
            raise FilePresignedUrlGenerationFailedException(
                detail=f"Failed to generate presigned URL for file with client_ref_id={file_metadata.client_ref_id}.",
            ) from exc

        result = PresignedURLWithRefDTO(
            file_id=file_id,
            presigned_url=AnyHttpUrl(url),
            client_ref_id=file_metadata.client_ref_id,
        )

        await self._redis_client.finalize_idempotency_key(
            scope=idem_scope,
            user_id=user_id,
            key=idempotency_key,
            ttl=self._IDEMPOTENCY_KEY_TTL,
            response=self._serialize_idempotency_response([result], []),
        )

        return result

    async def get_upload_presigned_urls(
        self,
        files_metadata: list[FileMetadataDTO],
        user_id: UUID,
        idempotency_key: UUID,
    ) -> UploadFilesResult:
        """Получение presigned-url для загрузки нескольких файлов напрямую в S3.

        Принимает список метаданных файлов, валидирует каждый из них и генерирует
        presigned URL для прямой загрузки в S3. Файлы, не прошедшие валидацию
        или для которых не удалось сгенерировать URL, возвращаются отдельным списком ошибок.

        В отличие от get_upload_presigned_url, ошибки валидации отдельных файлов
        не прерывают обработку - они накапливаются и возвращаются в составе результата.

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
        UploadFilesResult
            Кортеж из двух списков:
            - первый - успешно сгенерированные presigned URLs;
            - второй - ошибки для файлов, которые не прошли валидацию
            или для которых генерация URL завершилась неудачей.

        Raises
        ------
        IdempotencyException
            Если запрос с переданным ключом идемпотентности уже находится в процессе обработки.
        """
        idem_scope = "media_upload_batch_direct"

        is_new, cached = await self._idempotency_gate(
            idem_scope, user_id, idempotency_key, not_null=True
        )
        if not is_new:
            raws = json.loads(cached)
            return (
                [
                    PresignedURLWithRefDTO.model_validate_json(r)
                    for r in raws["successful"]
                ],
                [UploadFileErrorDTO.model_validate_json(r) for r in raws["failed"]],
            )

        valid_files: list[FileMetadataDTO] = []
        failed: list[UploadFileErrorDTO] = []

        for metadata in files_metadata:
            try:
                valid_files.append(self._validate_file_for_upload(metadata))
            except MediaDomainException as exc:
                failed.append(
                    self._map_upload_exception_to_error_dto(exc, metadata.client_ref_id)
                )

        if not valid_files:
            await self._redis_client.finalize_idempotency_key(
                scope=idem_scope,
                user_id=user_id,
                key=idempotency_key,
                ttl=self._IDEMPOTENCY_KEY_TTL,
                response=self._serialize_idempotency_response([], failed),
            )
            return [], failed

        batch_id = uuid4()

        object_keys = [
            self._generate_object_key(user_id, batch_id) for _ in valid_files
        ]
        file_ids = await self._file_repo.add_pending_files(
            valid_files, object_keys, user_id
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
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful: list[PresignedURLWithRefDTO] = []
        failed_file_ids: list[UUID] = []

        for file_id, metadata, result in zip(file_ids, valid_files, results):
            if isinstance(result, BaseException):
                failed_file_ids.append(file_id)

                failed.append(
                    UploadFileErrorDTO(
                        client_ref_id=metadata.client_ref_id,
                        code=UploadFileErrorCode.GENERATION_FAILED,
                        message=f"Unexpected error while generating URL for file {metadata.client_ref_id}",
                    )
                )
            else:
                successful.append(
                    PresignedURLWithRefDTO(
                        file_id=file_id,
                        presigned_url=AnyHttpUrl(result),
                        client_ref_id=metadata.client_ref_id,
                    )
                )

        if failed_file_ids:
            await self._file_repo.delete_pending_files_by_ids(failed_file_ids)

        await self._redis_client.finalize_idempotency_key(
            scope=idem_scope,
            user_id=user_id,
            key=idempotency_key,
            ttl=self._IDEMPOTENCY_KEY_TTL,
            response=self._serialize_idempotency_response(successful, failed),
        )

        return successful, failed

    def _validate_file_for_upload(
        self, file_metadata: FileMetadataDTO
    ) -> FileMetadataDTO:
        """Проверяет, что тип файла входит в список поддерживаемых.

        Parameters
        ----------
        file_metadata : FileMetadataDTO
            Метаданные файла для валидации.

        Returns
        -------
        FileMetadataDTO
            Те же метаданные, если файл прошёл проверку.

        Raises
        ------
        UnsupportedFileTypeException
            Если content_type файла не входит в _SUPPORTED_CONTENT_TYPES.
        """
        if file_metadata.content_type not in self._SUPPORTED_CONTENT_TYPES:
            raise UnsupportedFileTypeException(
                detail=(
                    f"File types '{file_metadata.content_type}' is not supported. "
                    f"Supported types: {self._SUPPORTED_CONTENT_TYPES}."
                )
            )

        return file_metadata

    def _map_upload_exception_to_error_dto(
        self, exc: MediaDomainException, client_ref_id: str
    ) -> UploadFileErrorDTO:
        """Преобразует доменное исключение загрузки файла в DTO ошибки.

        Используется для формирования списка failed-файлов в batch-операциях,
        когда ошибка одного файла не должна прерывать обработку остальных.

        Parameters
        ----------
        exc : MediaDomainException
            Исключение, возникшее при обработке файла.
        client_ref_id : str
            Клиентский идентификатор файла, при обработке которого возникла ошибка.

        Returns
        -------
        UploadFileErrorDTO
            DTO с кодом ошибки, client_ref_id и сообщением из исключения.

        Raises
        ------
        Exception
            Если тип исключения не предусмотрен маппингом (re-raise через `raise`).
        """
        match exc:
            case UnsupportedFileTypeException():
                code = UploadFileErrorCode.UNSUPPORTED_FILE_TYPE
            case _:
                raise

        return UploadFileErrorDTO(
            client_ref_id=client_ref_id, code=code, message=exc.detail
        )

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
        files = await self._file_repo.get_files_by_ids([file_id], user_id)

        if len(files) != 1:
            raise MediaNotFoundException(
                media_type="file",
                detail=f"File with id={file_id} not found, or you're not this file's creator.",
            )

        file = files[0]

        if file.status == FileStatus.UPLOADED:
            return

        try:
            await self._s3_client.head_object(
                Bucket=self._settings.MINIO_BUCKET_NAME,
                Key=file.object_key,
            )
        except ClientError:
            raise UploadNotCompletedException(
                detail=f"File with id={file_id} has not been found in object storage yet.",
            )

        await self._file_repo.mark_file_uploaded(file.id)
        await self._redis_client.increment_count("files", user_id)

    async def get_download_presigned_url(
        self, file_id: UUID, user_id: UUID
    ) -> PresignedURLDTO:
        """Генерирует presigned URL для скачивания файла из приватного хранилища.

        Определяет партнёра пользователя и запрашивает файл из репозитория
        с учётом прав доступа - файл доступен только владельцу или его партнёру.
        Валидирует статус файла и генерирует временную ссылку через S3-клиент.

        Parameters
        ----------
        file_id : UUID
            Идентификатор запрашиваемого файла.
        user_id : UUID
            Идентификатор пользователя, запросившего скачивание.

        Returns
        -------
        PresignedURLDTO
            DTO с идентификатором файла и сгенерированной presigned URL.
            Время жизни ссылки определяется настройкой
            ``settings.PRESIGNED_URL_EXPIRATION``.

        Raises
        ------
        MediaNotFoundException
            Файл не найден, был удалён или недоступен пользователю.
        FileUploadPendingException
            Файл ещё не загружен в хранилище (статус ``PENDING``).
            Клиент может повторить запрос позже.
        FileUploadFailedException
            Загрузка файла завершилась ошибкой (статус ``FAILED``).
            Повторный запрос без повторной загрузки файла бессмысленен.
        FileInvalidStatusException
            Статус файла в БД не распознан бизнес-логикой. Сигнализирует
            о баге или рассинхроне схемы БД с кодом приложения.
        """
        partner_id = await self._couple_repo.get_partner_id_by_user_id(user_id)

        file = await self._file_repo.get_file_by_id(file_id, user_id, partner_id)

        validated_file = self._validate_file_for_download(file, file_id)

        try:
            url = await self._s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._settings.MINIO_BUCKET_NAME,
                    "Key": validated_file.object_key,
                },
                ExpiresIn=self._settings.PRESIGNED_URL_EXPIRATION,
            )
        except Exception as exc:
            raise FilePresignedUrlGenerationFailedException(
                detail=f"Failed to generate presigned URL for file with id={file_id}.",
            ) from exc

        return PresignedURLDTO(file_id=validated_file.id, presigned_url=AnyHttpUrl(url))

    async def get_download_presigned_urls(
        self, files_uuids: list[UUID], user_id: UUID
    ) -> DownloadFilesResult:
        """Генерирует presigned URL для скачивания файлов.

        Для каждого запрошенного файла проверяет доступность и генерирует
        временную ссылку для скачивания из S3-совместимого хранилища.
        Файлы, недоступные для скачивания или при ошибке генерации URL,
        попадают в список ошибок - остальные обрабатываются независимо.

        Parameters
        ----------
        files_uuids : list[UUID]
            Список идентификаторов запрашиваемых файлов.
        user_id : UUID
            Идентификатор пользователя, запрашивающего скачивание.
            Используется для фильтрации файлов - доступны только файлы,
            принадлежащие пользователю или его партнёру.

        Returns
        -------
        DownloadFilesResult
            Кортеж из двух списков:

            - ``successful`` - presigned URL для файлов, успешно прошедших
            валидацию и генерацию ссылки;
            - ``failed`` - ошибки для файлов, которые не удалось обработать.
        """
        partner_id = await self._couple_repo.get_partner_id_by_user_id(user_id)

        files = {
            file.id: file
            for file in await self._file_repo.get_files_by_ids(
                files_uuids, user_id, partner_id
            )
        }

        valid_files: list[FileDTO] = []
        failed: list[DownloadFileErrorDTO] = []

        for file_id in files_uuids:
            try:
                valid_files.append(
                    self._validate_file_for_download(files.get(file_id), file_id)
                )
            except FileInvalidStatusException:
                raise  # пробрасывается наверх, т.к. является неожиданным состоянием системы
            except MediaDomainException as exc:
                failed.append(self._map_download_exception_to_error_dto(exc, file_id))

        tasks = [
            self._s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._settings.MINIO_BUCKET_NAME,
                    "Key": file.object_key,
                },
                ExpiresIn=self._settings.PRESIGNED_URL_EXPIRATION,
            )
            for file in valid_files
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful: list[PresignedURLDTO] = []

        for file, result in zip(valid_files, results):
            if isinstance(result, BaseException):
                failed.append(
                    DownloadFileErrorDTO(
                        file_id=file.id,
                        code=DownloadFileErrorCode.GENERATION_FAILED,
                        message=f"Unexpected error occurred while generating URL for file with id={file.id}",
                    )
                )
            else:
                successful.append(
                    PresignedURLDTO(file_id=file.id, presigned_url=AnyHttpUrl(result))
                )

        return successful, failed

    def _validate_file_for_download(
        self, file: FileDTO | None, file_id: UUID
    ) -> FileDTO:
        """Проверяет доступность файла для скачивания.

        Parameters
        ----------
        file : FileDTO | None
            DTO файла, полученный из хранилища. None означает,
            что файл не найден или недоступен текущему пользователю.
        file_id : UUID
            Идентификатор запрашиваемого файла. Используется
            для формирования сообщений об ошибках.

        Returns
        -------
        FileDTO
            Если файл существует и имеет статус ``UPLOADED``.

        Raises
        ------
        MediaNotFoundException
            Файл не найден или недоступен пользователю.
        FileUploadPendingException
            Файл ещё загружается (статус ``PENDING``).
        FileUploadFailedException
            Загрузка завершилась ошибкой (статус ``FAILED``).
        FileDeletedException
            Файл был удалён (статус ``DELETED``).
        FileInvalidStatusException
            Файл находится в неожиданном статусе.
        """
        if file is None:
            raise MediaNotFoundException(
                media_type="file",
                detail=f"File with id={file_id} not found, or you're not this file's creator.",
            )

        if file.status == FileStatus.UPLOADED:
            return file

        match file.status:
            case FileStatus.PENDING:
                raise FileUploadPendingException(
                    detail=f"File with id={file_id} is now uploading.",
                )
            case FileStatus.FAILED:
                raise FileUploadFailedException(
                    detail=f"There were an error while uploading file with id={file_id}. File not accessible.",
                )
            case FileStatus.DELETED:
                raise FileDeletedException(
                    detail=f"File with id={file_id} has been deleted.",
                )
            case _:
                raise FileInvalidStatusException(
                    detail=f"File with id={file_id} not available.",
                )

    def _map_download_exception_to_error_dto(
        self, exc: MediaDomainException, file_id: UUID
    ) -> DownloadFileErrorDTO:
        """Маппит доменное исключение валидации файла в :class:`DownloadFileErrorDTO`.

        Преобразует известные исключения скачивания в DTO с соответствующим
        кодом ошибки. `FileInvalidStatusException` не маппится -
        сигнализирует о баге и должен всплыть до верхнего обработчика как HTTP 500.

        Parameters
        ----------
        exc : MediaDomainException
            Исключение, выброшенное :meth:`_validate_file_for_download`.
        file_id : UUID
            Идентификатор файла, включается в результирующий DTO.

        Returns
        -------
        DownloadFileErrorDTO
            DTO с кодом ошибки, соответствующим типу исключения:

            - :class:`MediaNotFoundException` -> ``NOT_FOUND``
            - :class:`FileUploadPendingException` -> ``UPLOAD_PENDING``
            - :class:`FileUploadFailedException` -> ``UPLOAD_FAILED``
            - :class:`FileDeletedException` -> ``FILE_DELETED``

        Raises
        ------
        FileInvalidStatusException
            Пробрасывается без маппинга. Не должно возвращаться клиенту -
            только логироваться и преобразовываться в HTTP 500.
        MediaDomainException
            Пробрасывается, если передан неизвестный подтип исключения.
            Сигнализирует о том, что mapper не был обновлён после добавления
            нового исключения.
        """
        match exc:
            case MediaNotFoundException():
                code = DownloadFileErrorCode.NOT_FOUND
            case FileUploadPendingException():
                code = DownloadFileErrorCode.UPLOAD_PENDING
            case FileUploadFailedException():
                code = DownloadFileErrorCode.UPLOAD_FAILED
            case FileDeletedException():
                code = DownloadFileErrorCode.FILE_DELETED
            case _:
                raise

        return DownloadFileErrorDTO(file_id=file_id, code=code, message=exc.detail)

    async def update_file(
        self, file_id: UUID, patch_file_dto: PatchFileDTO, user_id: UUID
    ) -> None:
        """Обновление атрибутов медиа-файла по его UUID.

        Передаёт данные в репозиторий для обновления альбома с учётом прав доступа.
        Обновляет только явно переданные поля (не равные `UNSET`).

        Parameters
        ----------
        file_id : UUID
            UUID файла к изменению.
        patch_file_dto : PatchFileDTO
            DTO с полями для обновления. Содержит только явно переданные поля.
        user_id : UUID
            UUID пользователя, инициирующего изменение файла.

        Raises
        ------
        NothingToUpdateException
            Не было передано ни одного поля на обновление.
        MediaNotFoundException
            Если файл не найден или пользователь не является его создателем.
        """
        if patch_file_dto.is_empty():
            raise NothingToUpdateException(detail="No fields provided for update.")

        updated = await self._file_repo.update_file_by_id(
            file_id, patch_file_dto, user_id
        )

        if not updated:
            raise MediaNotFoundException(
                media_type="file",
                detail=f"File with id={file_id} not found, or you're not this file's creator.",
            )

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
        files = await self._file_repo.get_files_by_ids([file_id], user_id)

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

        await self._file_repo.delete_file_by_id(file_id)
        await self._redis_client.decrement_count("files", user_id)
