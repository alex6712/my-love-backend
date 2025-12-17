from pydantic import BaseModel


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

    class Config:
        from_attributes = True
