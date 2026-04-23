DEFAULT_OFFSET = 0
"""Значение смещения по умолчанию для пагинации."""

MAX_OFFSET = 250
"""Максимально допустимое смещение для пагинации."""

DEFAULT_LIMIT = 10
"""Количество элементов на странице по умолчанию."""

MAX_LIMIT = 50
"""Максимально допустимое количество элементов на странице."""

if DEFAULT_OFFSET > MAX_OFFSET:
    raise ValueError(
        f"Default offset value({DEFAULT_OFFSET}) can't be larger than max value ({MAX_OFFSET})!"
    )

if DEFAULT_LIMIT > MAX_LIMIT:
    raise ValueError(
        f"Default limit value ({DEFAULT_LIMIT}) can't be larger than max value ({MAX_LIMIT})!"
    )
