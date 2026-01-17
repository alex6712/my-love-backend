from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseDTO(BaseModel):
    """Базовый класс Data Transfer Object (DTO) для всех объектов.

    Attributes
    ----------
    (Атрибуты определяются в дочерних классах)

    Notes
    -----
    Наследует конфигурацию Pydantic BaseModel с включенной поддержкой
    преобразования из атрибутов объектов (ORM mode).
    """

    model_config = ConfigDict(
        from_attributes=True,
    )


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
    """

    id: UUID
    created_at: datetime
