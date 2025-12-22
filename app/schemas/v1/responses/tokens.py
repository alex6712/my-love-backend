from pydantic import Field

from .standard import StandardResponse


class TokensResponse(StandardResponse):
    """Модель ответа сервера с вложенной парой JWT.

    Используется в качестве ответа с сервера на запрос на авторизацию.

    Attributes
    ----------
    access_token : str
        JSON Web Token, токен доступа.
    refresh_token : str
        JSON Web Token, токен обновления.
    token_type : str
        Тип возвращаемого токена.
    """

    access_token: str = Field(
        description="Значение токена доступа",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
            ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        ],
    )
    refresh_token: str = Field(
        description="Значение токена обновления",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
            ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        ],
    )
    token_type: str = Field(
        default="bearer",
        description="Тип токенов",
        examples=["bearer"],
    )
