from fastapi import status
from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    """Стандартная модель ответа сервера.

    Используется в качестве базовой модели ответа для любого запроса к этому приложению.

    Это означает, что любой ответ с сервера будет содержать код ответа ``code``
    и сообщение с сервера ``message`` в теле ответа.

    See Also
    --------
    pydantic.BaseModel

    Attributes
    ----------
    code : int
        HTTP-код ответа сервера.
    message : str
        Сообщение с сервера.
    """

    code: int = Field(default=status.HTTP_200_OK, examples=[status.HTTP_200_OK])
    message: str = Field(default="Success!", examples=["Success!"])
