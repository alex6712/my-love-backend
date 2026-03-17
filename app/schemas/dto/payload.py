from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer


class Payload(BaseModel):
    """Структура JWT payload.

    Attributes
    ----------
    sub : UUID
        Субъект токена — идентификатор пользователя.
    iat : datetime
        Время выпуска токена (issued at).
    exp : datetime
        Время истечения токена (expiration time).
    jti : UUID
        Уникальный идентификатор токена (JWT ID).
    iss : str
        Издатель токена (issuer).
    session_id : UUID
        Идентификатор сессии пользователя.
    """

    sub: UUID
    iat: datetime
    exp: datetime
    jti: UUID
    iss: str
    session_id: UUID

    @field_serializer("iat", "exp")
    def serialize_datetime(self, value: datetime) -> int:
        return int(value.timestamp())

    def to_jwt_payload(self) -> dict[str, str | int]:
        """Сериализует payload для передачи в `_jwt_encode`.

        Конвертирует UUID в строки, datetime в Unix timestamp (int).

        Returns
        -------
        dict[str, str | int]
            Сериализованный payload, готовый к кодированию.
        """
        return self.model_dump(mode="json")

    model_config = ConfigDict(frozen=True)
