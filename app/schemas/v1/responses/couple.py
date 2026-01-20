from pydantic import Field

from app.schemas.dto.couples import CoupleRequestDTO
from app.schemas.v1.responses.standard import StandardResponse


class CoupleRequestsResponse(StandardResponse):
    """Модель ответа сервера с вложенным списком запросов на создание пары.

    Используется в качестве ответа с сервера на запрос о получении
    запросов на создание пары.

    Attributes
    ----------
    requests : list[CoupleRequestDTO]
        Список всех запросов, подходящих под фильтры.
    """

    requests: list[CoupleRequestDTO] = Field(
        description="Список всех запросов, подходящих под фильтры.",
    )
