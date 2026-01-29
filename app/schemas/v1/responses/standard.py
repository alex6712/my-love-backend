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
