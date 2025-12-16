from pydantic import Field, EmailStr

from .standard import StandardResponse


class AppInfoResponse(StandardResponse):
    """Модель ответа на запрос информации о приложении.

    См. ``StandardResponse`` для получения информации об унаследованных атрибутах.

    See Also
    --------
    .standard.StandardResponse

    Attributes
    ----------
    app_name : str
        Название приложения.
    app_version : str
        Текущая версия приложения.
    app_description : str
        Полное описание приложения.
    app_summary : str
        Краткое описание приложения.
    admin_name : str
        Имя ответственного лица.
    admin_email : str
        Адрес электронной почты для связи с ответственным лицом.
    """

    app_name: str = Field(examples=["Fast API"])
    app_version: str = Field(examples=["0.0.0"])
    app_description: str = Field(examples=["REST API using FastAPI Python 3.12"])
    app_summary: str = Field(examples=["The best web-application."])
    admin_name: str = Field(examples=["John Doe"])
    admin_email: EmailStr = Field(examples=["john.doe@gmail.com"])
