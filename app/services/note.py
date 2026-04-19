from uuid import UUID

from app.core.enums import NoteType, SortOrder
from app.core.exceptions.base import NothingToUpdateException
from app.core.exceptions.note import NoteNotFoundException
from app.infra.postgres.uow import UnitOfWork
from app.infra.redis import RedisClient
from app.repositories.interface import AccessContext
from app.repositories.note import NoteRepository
from app.schemas.dto.note import CreateNoteDTO, FilterNoteDTO, NoteDTO, UpdateNoteDTO


class NoteService:
    """Сервис работы с пользовательскими заметками.

    Реализует бизнес-логику для менеджмента пользовательских заметок.
    Здесь представлены все основные CRUD операции над заметками
    в приложении.

    Attributes
    ----------
    _redis_client : RedisClient
        Клиент Redis для кэширования запросов.
    _note_repo : NoteRepository
        Репозиторий для операций с заметками в БД.

    Methods
    -------
    create_note(create_dto, user_id)
        Создание новой пользовательской заметки.
    get_notes(note_type, offset, limit, sort_order, user_id)
        Получение всех заметок по UUID создателя.
    count_notes(user_id)
        Получение количества всех доступных пользователю заметок.
    update_note(note_id, title, content, user_id)
        Обновление атрибутов заметки по его UUID.
    delete_note(note_id, user_id)
        Удаление заметки по его UUID.
    """

    _COUNT_CACHE_TTL = 3600
    """Время в секундах, которое живёт кэш счётчика записей."""

    def __init__(self, unit_of_work: UnitOfWork, redis_client: RedisClient):
        self._redis_client = redis_client

        self._note_repo = unit_of_work.get_repository(NoteRepository)

    async def create_note(self, create_dto: CreateNoteDTO, user_id: UUID) -> None:
        """Создание новой пользовательской заметки.

        Создаёт новую заметку по переданным данным.
        Инкрементирует счётчик в Redis.

        Parameters
        ----------
        type : NoteType
            Тип пользовательской заметки.
        title : str
            Заголовок пользовательской заметки
        content : str
            Содержимое пользовательской заметки.
        user_id : UUID
            UUID пользователя, создающего заметку.
        """
        await self._note_repo.create(create_dto, user_id)
        await self._redis_client.increment_count("notes", user_id)

    async def get_notes(
        self,
        note_type: NoteType | None,
        offset: int,
        limit: int,
        sort_order: SortOrder,
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> tuple[list[NoteDTO], int]:
        """Получение всех заметок по UUID создателя.

        Получает на вход UUID пользователя, ищет UUID партнёра,
        возвращает список всех заметок, которые доступны пользователю (
        созданы им или его партнёром).

        Parameters
        ----------
        note_type : NoteType | None
            Тип заметок для получения.
        offset : int
            Смещение от начала списка (количество пропускаемых заметок).
        limit : int
            Количество возвращаемых заметок.
        sort_order : SortOrder
            Направление сортировки заметок.
        user_id : UUID
            UUID пользователя.
        partner_id : UUID | None, optional
            UUID партнёра пользователя или None.

        Returns
        -------
        tuple[list[NoteDTO], int]
            Кортеж из списка заметок и общего количества.
        """
        return await self._note_repo.get_all(
            FilterNoteDTO(type=note_type),
            AccessContext(user_id=user_id, partner_id=partner_id),
            offset=offset,
            limit=limit,
            sort_order=sort_order,
        )

    async def count_notes(self, user_id: UUID, partner_id: UUID | None = None) -> int:
        """Получение количества всех доступных пользователю заметок.

        Возвращает закэшированное значение из Redis, если оно есть.
        В случае cache miss обращается к БД и прогревает кэш.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя.
        partner_id : UUID | None, optional
            UUID партнёра пользователя или None.

        Returns
        -------
        int
            Количество доступных пользователю заметок.
        """
        if cached := await self._redis_client.get_count("notes", user_id):
            return cached

        count = await self._note_repo.count(
            AccessContext(user_id=user_id, partner_id=partner_id)
        )

        await self._redis_client.set_count(
            "notes", user_id, count, self._COUNT_CACHE_TTL
        )

        return count

    async def update_note(
        self,
        note_id: UUID,
        update_dto: UpdateNoteDTO,
        user_id: UUID,
        partner_id: UUID | None = None,
    ) -> None:
        """Частичное обновление атрибутов заметки по её UUID.

        Получает идентификатор партнёра текущего пользователя и передаёт данные
        в репозиторий для обновления заметки с учётом прав доступа.
        Обновляет только явно переданные поля (не равные `UNSET`).

        Parameters
        ----------
        note_id : UUID
            UUID заметки к изменению.
        update_dto : UpdateNoteDTO
            DTO с полями для обновления. Содержит только явно переданные поля.
        user_id : UUID
            UUID пользователя, инициирующего изменение заметки.
        partner_id : UUID | None, optional
            UUID партнёра пользователя или None.

        Raises
        ------
        NothingToUpdateException
            Не было передано ни одного поля на обновление.
        NoteNotFoundException
            Если заметка не найдена или пользователь не является её создателем.
        """
        if update_dto.is_empty():
            raise NothingToUpdateException(detail="No fields provided for update.")

        if not await self._note_repo.update(
            note_id,
            update_dto,
            AccessContext(user_id=user_id, partner_id=partner_id),
        ):
            raise NoteNotFoundException(
                detail=f"Note with id={note_id} not found, or you're not this note's creator.",
            )

    async def delete_note(self, note_id: UUID, user_id: UUID) -> None:
        """Удаление заметки по его UUID.

        Получает UUID заметки и UUID пользователя, совершающего действие удаления.
        Если UUID пользователя не совпадает с UUID создателя заметки, завершает
        действие исключением. В ином случае удаляет заметку.

        Декрементирует счётчик заметок в Redis.

        Parameters
        ----------
        note_id : UUID
            UUID заметки к удалению.
        user_id : UUID
            UUID пользователя, запрашивающего удаление.

        Raises
        ------
        NoteNotFoundException
            Возникает в случае, если заметка с переданным UUID не существует
            или текущий пользователь не является создателем заметки.
        """
        if not await self._note_repo.delete(note_id, AccessContext(user_id=user_id)):
            raise NoteNotFoundException(
                detail=f"Note with id={note_id} not found, or you're not this note's creator.",
            )

        await self._redis_client.decrement_count("notes", user_id)
