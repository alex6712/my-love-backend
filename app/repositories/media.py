from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.album import AlbumModel
from app.repositories.interface import RepositoryInterface


class MediaRepository(RepositoryInterface):
    """Репозиторий медиа альбомов и файлов.

    Реализация паттерна Репозиторий. Является объектом доступа к данным (DAO).
    Реализует основные CRUD операции с различными типами медиа.

    Attributes
    ----------
    session : AsyncSession
        Объект асинхронной сессии запроса.

    Methods
    -------
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add_album(
        self,
        title: str,
        description: str,
        created_by: UUID,
        is_private: bool = False,
    ) -> None:
        """Добавляет в базу данных новую запись о медиа альбоме.

        Parameters
        ----------
        title : str
            Наименование альбома.
        description : str
            Описание альбома.
        created_by : UUID
            UUID пользователя, создавшего альбом.
        is_private : bool
            Видимость альбома:
            - True - личный альбом;
            - False - публичный альбом (значение по умолчанию).
        """
        self.session.add(
            AlbumModel(
                title=title,
                description=description,
                is_private=is_private,
                created_by=created_by,
            )
        )

    async def get_album_by_id(self, id_: UUID) -> None:
        """Возвращает DTO медиа альбома по его id.

        Parameters
        ----------
        id_ : UUID
            UUID пользователя.

        Returns
        -------
        UserDTO
            DTO записи пользователя.
        """
        pass
