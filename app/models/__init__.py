"""SQLAlchemy-модели таблиц базы данных.

В этом модуле сохранены модели таблиц базы данных.
См. раздел `Notes` для дополнительной важной информации.

Notes
-----
Инициализация моделей SQAlchemy.

Для инициализации `metadata` базовой модели нужно инициализировать
все остальные модели, от неё наследованные.

Это можно сделать, импортировав их в любом месте программы.
Однако скрипт Alembic работает отдельно от всего остального кода,
и поэтому ему нужен свой механизм инициализации моделей.

Это можно сделать либо в `./alembic/env.py`, либо здесь, т.к.
модуль `models` обязательно будет инициализирован при импорте
`BaseModel`.
"""

from .album import AlbumModel
from .user import UserModel
from .couple import CoupleRequestModel
from .file import FileModel
from .album_items import AlbumItemsModel
