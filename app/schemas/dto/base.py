from pydantic import BaseModel, ConfigDict


class BaseDTO(BaseModel):
    """Базовый класс Data Transfer Object (DTO) для всех моделей.

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
