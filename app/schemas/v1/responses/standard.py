from pydantic import BaseModel, Field

from app.core.enums import APICode


class BaseResponse(BaseModel):
    """Базовая модель ответа сервера.

    Используется в качестве базовой модели ответа для
    любого запроса к этому приложению.

    Это означает, что любой ответ с сервера будет содержать
    код ответа ``code``в теле ответа.

    See Also
    --------
    pydantic.BaseModel

    Attributes
    ----------
    code : int
        HTTP-код ответа сервера.
    """

    code: APICode = Field(
        default=APICode.SUCCESS,
        description="Статус ответа от сервера в виде API Enum",
        examples=[APICode.SUCCESS],
    )


class StandardResponse(BaseResponse):
    """Стандартная модель ответа сервера.

    Используется в качестве стандартной модели ответа с сообщением
    для любого запроса к этому приложению.

    Это означает, что любой ответ с сервера будет содержать
    сообщение с сервера ``detail`` в теле ответа.

    Attributes
    ----------
    detail : str
        Сообщение с сервера.
    """

    detail: str = Field(
        default="Success!",
        description="Сообщение о выполненных на сервере действиях",
        examples=["Success!"],
    )


class PaginationResponse(StandardResponse):
    """Модель ответа сервера с полем total для пагинации.

    Используется в качестве ответа с сервера на запрос о получении
    различных списков с пагинацией и необходимостью получения
    общего количества записей.

    Attributes
    ----------
    total : int
        Общее количество записей, доступных пользователю.
    """

    total: int = Field(
        description="Общее количество записей, доступных пользователю.",
    )


class CountResponse(StandardResponse):
    """Модель ответа сервера с количеством записей.

    Используется в качестве модели ответа для эндпоинтов,
    возвращающих общее количество записей какой-либо сущности.

    Attributes
    ----------
    count : int
        Общее количество записей.
    """

    count: int = Field(
        description="Общее количество записей",
    )
