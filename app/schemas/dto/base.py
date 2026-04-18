from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.types import Unset


class BaseDTO(BaseModel):
    """Базовый класс Data Transfer Object (DTO) для всех объектов.

    Attributes
    ----------
    (Атрибуты определяются в дочерних классах)
    """

    pass


class BaseSQLCoreDTO(BaseDTO):
    """Базовый класс DTO для представления записей таблиц при работе с SQLAlchemy Core.

    Определяет общие атрибуты (столбцы), присутствующие в большинстве таблиц,
    предоставляя единообразный интерфейс для всех наследуемых DTO.

    Attributes
    ----------
    id : UUID
        Уникальный идентификатор записи.
    created_at : datetime
        Временная метка создания записи.

    Notes
    -----
    Наследует конфигурацию Pydantic BaseModel с включённой поддержкой
    преобразования из объектов SQLAlchemy Core (например, `Row`) или словарей.
    """

    id: UUID
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class BaseRequestDTO(BaseDTO):
    """Базовый класс DTO для объектов, строящихся из входящих запросов.

    Предоставляет общий хелпер `_from_schema` для дочерних классов,
    не затрагивая DTO, не связанные с обработкой запросов.
    """

    @classmethod
    def _from_schema(cls, schema: BaseModel, **dump_kwargs: Any) -> Self:
        """Внутренний хелпер: создаёт DTO из Pydantic-схемы с произвольными параметрами dump.

        Parameters
        ----------
        schema : BaseModel
            Исходная схема запроса.
        **dump_kwargs : Any
            Аргументы, передаваемые в `model_dump()` (например, `exclude_unset=True`).
        """
        return cls(**schema.model_dump(**dump_kwargs))


class BaseCreateDTO(BaseRequestDTO):
    """Базовый DTO для создания новых сущностей.

    Предоставляет метод `from_request_schema` для построения DTO из схемы
    входящего POST-запроса и `to_create_values` для получения итогового словаря.

    Notes
    -----
    В отличие от `BasePatchDTO`, все поля считаются явно переданными —
    sentinel-тип `Unset` здесь не нужен.

    Examples
    --------
    >>> class CreateEntryDTO(BaseCreateDTO):
    ...     title: str
    ...     content: str | None = None
    ...
    >>> dto = CreateEntryDTO.from_request_schema(request_schema)
    >>> dto.to_create_values()
    {'title': 'Заголовок', 'content': None}
    """

    @classmethod
    def from_request_schema(cls, request_schema: BaseModel) -> Self:
        """Создаёт DTO из Pydantic-схемы POST-запроса.

        В отличие от `BasePatchDTO.from_request_schema`, включает **все** поля,
        в том числе те, что не были явно переданы (используются значения по умолчанию).

        Parameters
        ----------
        request_schema : BaseModel
            Pydantic-схема входящего запроса.

        Returns
        -------
        Self
            Экземпляр DTO со всеми полями.
        """
        return cls._from_schema(request_schema)

    def to_create_values(self) -> dict[str, Any]:
        """Возвращает словарь всех полей DTO.

        Returns
        -------
        dict[str, Any]
            Словарь вида {field_name: value} по всем полям модели.
        """
        return self.model_dump()


class BaseUpdateDTO(BaseRequestDTO):
    """Базовый DTO для обновления сущностей.

    Предоставляет метод `to_update_values` для извлечения только явно
    переданных полей, используя sentinel-тип `Unset` для различия между
    'поле не передано' и 'поле передано как None'.

    Notes
    -----
    Наследники должны объявлять все обновляемые поля с типом `Maybe[T]`
    и значением по умолчанию `UNSET`.

    Examples
    --------
    >>> class PatchEntryDTO(BaseUpdateDTO):
    ...     title: Maybe[str] = UNSET
    ...     content: Maybe[str | None] = UNSET
    ...     comment: Maybe[str | None] = UNSET
    ...
    >>> dto = PatchEntryDTO(title="Новый заголовок", content=None)
    >>> dto.to_update_values()
    {'title': 'Новый заголовок', 'content': None}
    """

    def __init__(self):
        self._cached_values: dict[str, Any] | None = None

    @classmethod
    def from_request_schema(cls, request_schema: BaseModel) -> Self:
        """Создаёт DTO из Pydantic-схемы запроса, сохраняя информацию о переданных полях.

        Извлекает только явно переданные поля из схемы запроса через
        `model_dump(exclude_unset=True)`, что позволяет корректно различать
        'поле не передано' и 'поле передано как None' на уровне DTO.

        Parameters
        ----------
        request_schema : BaseModel
            Pydantic-схема входящего запроса. Обычно это схема из слоя API
            (например, тело PATCH-запроса).

        Returns
        -------
        Self
            Экземпляр DTO, где переданные поля содержат реальные значения,
            а непереданные - значение `UNSET`.

        Notes
        -----
        Корректная работа метода зависит от того, что поля схемы запроса
        объявлены со значениями по умолчанию - иначе `exclude_unset=True`
        не даст нужного эффекта и все поля будут считаться "переданными".
        """
        return cls._from_schema(request_schema, exclude_unset=True)

    def _build_update_values(self) -> dict[str, Any]:
        """Формирует словарь значений для операции обновления.

        Исключает поля, которые не были явно переданы пользователем
        (имеют значение `UNSET`). Поля, переданные со значением `None`,
        сохраняются и включаются в результирующий словарь.

        Returns
        -------
        dict[str, Any]
            Словарь вида {field_name: value}, содержащий только явно
            переданные поля. Используется для формирования UPDATE-запроса.
        """
        return {
            field: value
            for field, value in self.model_dump().items()
            if not isinstance(value, Unset)
        }

    def to_update_values(self) -> dict[str, Any]:
        """Возвращает закэшированный словарь значений для обновления.

        При первом вызове формирует словарь через `_build_update_values`,
        после чего повторно использует сохранённый результат.

        Returns
        -------
        dict[str, Any]
            Словарь вида {field_name: value}, содержащий только явно
            переданные поля (без значений `UNSET`). Может содержать `None`,
            если поле было явно передано с таким значением.
        """
        if self._cached_values is None:
            self._cached_values = self._build_update_values()

        return self._cached_values

    def is_empty(self) -> bool:
        """Проверяет, что ни одно поле не было явно передано.

        Returns
        -------
        bool
            True, если все поля остались `UNSET`, False - если хотя бы
            одно поле было явно передано.
        """
        return not self.to_update_values()


class BaseErrorDTO[T](BaseModel):
    """Базовый generic-класс DTO для представления ошибок.

    Предоставляет единообразную структуру для всех DTO ошибок,
    параметризуя код ошибки конкретным enum-типом.

    Parameters
    ----------
    T : type
        Тип кода ошибки. Обычно - конкретный Enum,
        описывающий возможные ошибки соответствующей операции.

    Attributes
    ----------
    code : T
        Код ошибки. Тип определяется параметром T при наследовании.
    message : str
        Человекочитаемое описание ошибки.
    """

    code: T
    message: str
