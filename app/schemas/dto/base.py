from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.types import UNSET


class BaseDTO(BaseModel):
    """Базовый класс Data Transfer Object (DTO) для всех объектов.

    Attributes
    ----------
    (Атрибуты определяются в дочерних классах)
    """

    pass


class BasePatchDTO(BaseDTO):
    """Базовый DTO для частичного обновления сущностей.

    Предоставляет метод `to_update_values` для извлечения только явно
    переданных полей, используя sentinel-тип `Unset` для различия между
    'поле не передано' и 'поле передано как None'.

    Notes
    -----
    Наследники должны объявлять все обновляемые поля с типом `Maybe[T]`
    и значением по умолчанию `UNSET`.

    Examples
    --------
    >>> class PatchEntryDTO(BasePatchDTO):
    ...     title: Maybe[str] = UNSET
    ...     content: Maybe[str | None] = UNSET
    ...     comment: Maybe[str | None] = UNSET
    ...
    >>> dto = PatchEntryDTO(title="Новый заголовок", content=None)
    >>> dto.to_update_values()
    {'title': 'Новый заголовок', 'content': None}
    """

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
            а непереданные — значение `UNSET`.

        Notes
        -----
        Корректная работа метода зависит от того, что поля схемы запроса
        объявлены со значениями по умолчанию - иначе `exclude_unset=True`
        не даст нужного эффекта и все поля будут считаться "переданными".
        """
        return cls(**request_schema.model_dump(exclude_unset=True))

    def to_update_values(self) -> dict[str, Any]:
        """Возвращает словарь только из явно переданных полей.

        Returns
        -------
        dict[str, Any]
            Словарь вида {field_name: value} без полей со значением `UNSET`.
            Может содержать None, если поле явно передано как None.
        """
        return {
            field: value
            for field, value in self.model_dump().items()
            if value is not UNSET
        }


class BaseSQLModelDTO(BaseDTO):
    """Базовый класс DTO для всех SQL-моделей.

    Определяет атрибуты (столбцы), имеющиеся у базовой SQl модели приложения,
    предоставляя таким образом единообразный интерфейс для всех
    наследуемых DTO.

    Attributes
    ----------
    id : UUID
        Уникальный идентификатор объекта (записи).
    created_at : UUID
        Временная метка создания объекта (записи).

    Notes
    -----
    Наследует конфигурацию Pydantic BaseModel с включенной поддержкой
    преобразования из атрибутов объектов (ORM mode).
    """

    id: UUID
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
