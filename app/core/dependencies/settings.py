from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings

type SettingsDependency = Annotated[Settings, Depends(get_settings)]
"""Зависимость для endpoint, которые нуждаются в информации о приложении"""
