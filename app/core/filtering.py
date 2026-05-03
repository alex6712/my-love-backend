class FilterOp:
    """Базовый маркер оператора фильтрации.

    Используется как метаданные в аннотациях полей DTO через `Annotated`,
    чтобы указать, каким SQL-оператором поле должно участвовать в WHERE-условии.
    Репозиторий читает метаданные и строит выражение через соответствующий
    метод SQLAlchemy.

    Notes
    -----
    Не используется напрямую - только через конкретные подклассы.
    Если оператор для поля не задан явно, репозиторий выбирает дефолтный:
    `IN` для списков, `EQ` для скаляров.

    Examples
    --------
    >>> class UserFilterManyDTO(BaseFilterManyDTO):
    ...     ids: Annotated[Maybe[list[int]], IN] = UNSET   # явный оператор
    ...     status: Annotated[Maybe[str], EQ] = UNSET      # явный оператор
    ...     name: Annotated[Maybe[str]] = UNSET            # дефолт: EQ
    """

    pass


class EqOp(FilterOp):
    """Маркер оператора точного равенства (`field = value`).

    Применяется для скалярных значений, когда требуется точное совпадение.
    Является дефолтным оператором для скалярных полей, если маркер не задан.

    Examples
    --------
    >>> class UserFilterManyDTO(BaseFilterManyDTO):
    ...     is_active: Annotated[Maybe[bool], EQ] = UNSET
    ...     # -> WHERE is_active = true
    """

    pass


class InOp(FilterOp):
    """Маркер оператора проверки вхождения в множество (`field IN (values)`).

    Применяется для фильтрации по нескольким допустимым значениям.
    Является дефолтным оператором для полей с типом `list`, если маркер не задан.

    Notes
    -----
    Если значение поля является скаляром, а не списком, репозиторий автоматически
    оборачивает его в список перед построением условия.

    Examples
    --------
    >>> class UserFilterManyDTO(BaseFilterManyDTO):
    ...     ids: Annotated[Maybe[list[int]], IN] = UNSET
    ...     # -> WHERE id IN (1, 2, 3)
    """

    pass


class LikeOp(FilterOp):
    """Маркер оператора нечёткого поиска (`field ILIKE '%value%'`).

    Применяется для текстового поиска без учёта регистра.
    Репозиторий автоматически оборачивает значение в `%...%`.

    Notes
    -----
    Использует `ILIKE` вместо `LIKE` для независимости от регистра.
    Если требуется `LIKE` с учётом регистра - добавьте отдельный маркер `LikeCaseOp`.

    Examples
    --------
    >>> class UserFilterManyDTO(BaseFilterManyDTO):
    ...     name: Annotated[Maybe[str], LIKE] = UNSET
    ...     # -> WHERE name ILIKE '%kate%'
    """

    pass


class GteOp(FilterOp):
    """Маркер оператора "больше или равно" (`field >= value`).

    Применяется для фильтрации по нижней границе диапазона -
    числовых значений, дат, временных меток.

    Examples
    --------
    >>> class UserFilterManyDTO(BaseFilterManyDTO):
    ...     created_after: Annotated[Maybe[datetime], GTE, ColumnAlias("created_at")] = UNSET
    ...     # -> WHERE created_at >= '2024-01-01'
    """

    pass


class LteOp(FilterOp):
    """Маркер оператора "меньше или равно" (`field <= value`).

    Применяется для фильтрации по верхней границе диапазона -
    числовых значений, дат, временных меток.

    Examples
    --------
    >>> class UserFilterManyDTO(BaseFilterManyDTO):
    ...     created_before: Annotated[Maybe[datetime], LTE, ColumnAlias("created_at")] = UNSET
    ...     # -> WHERE created_at <= '2024-12-31'
    """

    pass


class IsNullOp(FilterOp):
    """Маркер оператора проверки на NULL (`field IS NULL` / `field IS NOT NULL`).

    Значение поля интерпретируется как булево:
    `True` -> `IS NULL`, `False` -> `IS NOT NULL`.

    Notes
    -----
    Отличается от остальных операторов тем, что значение поля не используется
    в условии напрямую, а лишь определяет направление проверки.

    Examples
    --------
    >>> class UserFilterManyDTO(BaseFilterManyDTO):
    ...     deleted: Annotated[Maybe[bool], IS_NULL, ColumnAlias("deleted_at")] = UNSET
    ...     # deleted=True  -> WHERE deleted_at IS NULL
    ...     # deleted=False -> WHERE deleted_at IS NOT NULL
    """

    pass


EQ = EqOp()
"""Единственный рекомендуемый экземпляр `EqOp`.

Используется как метаданные в `Annotated` для пометки полей с точным равенством.
"""

IN = InOp()
"""Единственный рекомендуемый экземпляр `InOp`.

Используется как метаданные в `Annotated` для пометки полей с фильтрацией по списку.
"""

LIKE = LikeOp()
"""Единственный рекомендуемый экземпляр `LikeOp`.

Используется как метаданные в `Annotated` для пометки текстовых полей с нечётким поиском.
"""

GTE = GteOp()
"""Единственный рекомендуемый экземпляр `GteOp`.

Используется как метаданные в `Annotated` для пометки полей с нижней границей диапазона.
"""

LTE = LteOp()
"""Единственный рекомендуемый экземпляр `LteOp`.

Используется как метаданные в `Annotated` для пометки полей с верхней границей диапазона.
"""

IS_NULL = IsNullOp()
"""Единственный рекомендуемый экземпляр `IsNullOp`.

Используется как метаданные в `Annotated` для пометки полей с проверкой на NULL.
"""


class ColumnAlias:
    """Маркер для явного маппинга поля DTO на колонку модели с другим именем.

    Используется как метаданные в аннотациях полей DTO через `Annotated`,
    когда имя поля DTO не совпадает с именем колонки в SQLAlchemy-модели.
    Репозиторий читает этот маркер перед обращением к `getattr(model, ...)`.

    Parameters
    ----------
    name : str
        Имя колонки в SQLAlchemy-модели, на которую маппится поле DTO.

    Notes
    -----
    Если маркер отсутствует, репозиторий использует имя поля DTO напрямую.
    Типичный случай применения - поля-диапазоны: `created_after` / `created_before`
    оба маппятся на одну колонку `created_at`.

    Examples
    --------
    >>> class UserFilterManyDTO(BaseFilterManyDTO):
    ...     created_after: Annotated[Maybe[datetime], GTE, ColumnAlias("created_at")] = UNSET
    ...     created_before: Annotated[Maybe[datetime], LTE, ColumnAlias("created_at")] = UNSET
    ...     # -> WHERE created_at >= '...' AND created_at <= '...'
    """

    def __init__(self, name: str) -> None:
        self.name = name
