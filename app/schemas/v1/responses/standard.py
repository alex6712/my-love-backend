from pydantic import BaseModel, Field

from app.core.enums import APICode


class StandardResponse(BaseModel):
    """Стандартная модель ответа сервера.

    Используется в качестве базовой модели ответа для любого запроса к этому приложению.

    Это означает, что любой ответ с сервера будет содержать код ответа ``code``
    и сообщение с сервера ``detail`` в теле ответа.

    See Also
    --------
    pydantic.BaseModel

    Attributes
    ----------
    code : int
        HTTP-код ответа сервера.
    detail : str
        Сообщение с сервера.
    """

    code: APICode = Field(
        default=APICode.SUCCESS,
        description="Статус ответа от сервера в виде API Enum",
        examples=[APICode.SUCCESS],
    )
    detail: str = Field(
        default="Success!",
        description="Сообщение о выполненных на сервере действиях",
        examples=["Success!"],
    )
