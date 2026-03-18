from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer


class _Payload(BaseModel):
    """Базовая структура JWT payload.

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


class RefreshTokenPayload(_Payload):
    """Payload refresh-токена.

    Представляет собой минимальный набор данных, необходимый для
    идентификации пользователя и сессии при обновлении access-токена.

    Используется исключительно для операции обновления токенов и не
    предназначен для авторизации запросов к защищённым ресурсам.

    В отличие от AccessTokenPayload, не предполагает расширения
    дополнительными claims, так как должен оставаться максимально
    стабильным и компактным.

    Notes
    -----
    - Используется как источник истины для продления сессии.
    - Должен содержать только критически необходимые данные.
    - Любые дополнительные claims следует добавлять только в access-токен.

    See Also
    --------
    AccessTokenPayload : Payload access-токена с расширяемыми claims.
    """

    pass


class AccessTokenPayload(_Payload):
    """Payload access-токена.

    Представляет собой расширяемую структуру данных, используемую
    для авторизации запросов к защищённым ресурсам.

    В отличие от RefreshTokenPayload, может содержать дополнительные
    claims (например, роли, permissions, feature flags и т.п.),
    необходимые для принятия решений на уровне бизнес-логики
    без обращения к базе данных.

    Предназначен для частого использования и передачи в каждом
    защищённом запросе, поэтому баланс между размером payload и
    количеством включённых данных должен быть тщательно контролируем.

    Attributes
    ----------
    couple_id : UUID | None
        Идентификатор пары пользователя. Используется в сценариях,
        где доступ к ресурсам зависит от дополнительного контекста,
        связанного с пользователем. Может отсутствовать.

    Notes
    -----
    - Может расширяться новыми полями без изменения refresh-токена.
    - Используется для авторизации (RBAC/ABAC и др.).
    - Должен оставаться достаточно компактным для эффективной передачи.

    See Also
    --------
    RefreshTokenPayload : Минимальный payload для обновления токенов.
    """

    couple_id: UUID | None


type AnyTokenPayload = AccessTokenPayload | RefreshTokenPayload
"""Обобщённый тип payload JWT-токенов.

Представляет объединение AccessTokenPayload и RefreshTokenPayload
и используется преимущественно в сигнатурах перегруженных функций
и методов, работающих с любым типом токена.

Позволяет описывать общий интерфейс обработки payload без
привязки к конкретному типу токена.

Notes
-----
- Не предназначен для создания экземпляров напрямую.
- В реализации может потребоваться уточнение типа через isinstance
  или pattern matching.
"""
