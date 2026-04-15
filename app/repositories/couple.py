from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.couple import CoupleModel
from app.repositories.interface import RepositoryInterface
from app.schemas.dto.couple import CoupleDTO, PatchCoupleDTO


class CoupleRepository(RepositoryInterface):
    """Репозиторий пар между пользователями.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с парами пользователей.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    add_couple(initiator_id, recipient_id)
        Регистрация пары между пользователями.
    get_couples_by_users_ids(first_user_id, second_user_id)
        Получение списка пар по UUID нескольких партнёров.
    get_partner_by_user_id(user_id)
        Получение информации о партнёре пользователя.
    update_couple_by_id(couple_id, patch_couple_dto, user_id)
        Обновление атрибутов пары между пользователями в базе данных.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def add_couple(self, user_low_id: UUID, user_high_id: UUID) -> None:
        """Создание записи о зарегистрированной паре между пользователями.

        Добавляет в базу данных запись о новой паре между пользователями.
        Уникальность и порядок UUID пользователей обеспечивается ограничениями
        базы данных.

        Parameters
        ----------
        user_low_id : UUID
            UUID пользователя-инициатора.
        user_high_id : UUID
            UUID пользователя-реципиента.
        """
        self.session.add(
            CoupleModel(user_low_id=user_low_id, user_high_id=user_high_id)
        )

    async def get_couples_by_partners_ids(self, *partners_ids: UUID) -> list[CoupleDTO]:
        """Получение списка пар по UUID нескольких партнёров.

        Parameters
        ----------
        *partner_ids : UUID
            Список UUID пользователей.

        Returns
        -------
        list[CoupleDTO]
            Список DTO пар, в которых состоит хотя бы один
            из переданных пользователей.
        """
        couples = await self.session.scalars(
            select(CoupleModel)
            .options(
                selectinload(CoupleModel.user_low),
                selectinload(CoupleModel.user_high),
            )
            .where(
                or_(
                    CoupleModel.user_low_id.in_(partners_ids),
                    CoupleModel.user_high_id.in_(partners_ids),
                )
            )
        )

        return [CoupleDTO.model_validate(couple) for couple in couples.all()]

    async def get_partner_id_by_user_id(self, user_id: UUID) -> UUID | None:
        """Получение UUID партнёра пользователя.

        Получает UUID пользователя, после чего ищет в БД запись
        о паре пользователей и возвращает UUID партнёра пользователя.

        Parameters
        ----------
        user_id : UUID
            UUID пользователя в системе.

        Returns
        -------
        UUID | None
            UUID партнёра пользователя или None, если пользователь не в паре.
        """
        couple = await self.session.scalar(
            select(CoupleModel).where(
                or_(
                    CoupleModel.user_low_id == user_id,
                    CoupleModel.user_high_id == user_id,
                ),
            )
        )

        if couple is None:
            return None

        return (
            couple.user_low_id
            if couple.user_high_id == user_id
            else couple.user_high_id
        )

    async def update_couple_by_id(
        self,
        couple_id: UUID,
        patch_couple_dto: PatchCoupleDTO,
        user_id: UUID,
    ) -> bool:
        """Обновление атрибутов пары между пользователями в базе данных.

        Выполняет SQL-запрос UPDATE для изменения атрибутов пары,
        устанавливая переданные в patch DTO значения.

        Parameters
        ----------
        couple_id : UUID
            UUID пары к изменению.
        patch_couple_dto : PatchCoupleDTO
            DTO с полями для обновления. Только явно переданные поля
            попадают в SET-часть запроса через `to_update_values()`.
        user_id : UUID
            UUID текущего пользователя.

        Returns
        -------
        bool
            True, если запись была обновлена, False - если пара
            не найдена или не прошла проверку прав доступа.
        """
        updated = await self.session.scalar(
            update(CoupleModel)
            .where(
                CoupleModel.id == couple_id,
                or_(
                    CoupleModel.user_low_id == user_id,
                    CoupleModel.user_high_id == user_id,
                ),
            )
            .values(**patch_couple_dto.to_update_values())
            .returning(CoupleModel.id)
        )

        return updated is not None
