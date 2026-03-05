import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import inspect, TIMESTAMP, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, AsyncSession
from app.config import settings

engine = create_async_engine(url=settings.DB_URL) # функция из SQLAlchemy 2.0+, предназначенная для создания асинхронного движка (async engine) для работы с БД в неблокирующем режиме
async_session_maker = async_sessionmaker(engine, class_=AsyncSession) # предназначенный для создания асинхронных сессий (AsyncSession) для работы с БД в неблокирующем режиме


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True                           # указывает, что класс модели не должен создавать таблицу в базе данных

    created_at: Mapped[datetime] = mapped_column( # Mapped[datetime]SQLAlchemy автоматически преобразует значения из БД в объекты datetime и обратно
        TIMESTAMP,                                #тип данных для хранения даты и времени
        server_default=func.now()                 # генерирует SQL‑выражение NOW()
    )
    updated_at: Mapped[datetime] = mapped_column( # mapped_column() — это основная конструкция в SQLAlchemy 2.0+ для объявления колонок таблицы в декларативных ORM‑моделях
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()                      # SQLAlchemy автоматически обновляет поле до текущего времени сервера БД при каждом изменении записи (UPDATE)
    )

    def to_dict(self, exclude_none: bool = False):
        """
        Преобразует объект модели в словарь.

        Args:
            exclude_none (bool): Исключать ли None значения из результата

        Returns:
            dict: Словарь с данными объекта
        """
        result = {}
        for column in inspect(self.__class__).columns:
            value = getattr(self, column.key)

            # Преобразование специальных типов данных
            if isinstance(value, datetime):    # isinstance() в Python проверяет, принадлежит ли объект указанному классу или типу
                value = value.isoformat()      # isoformat() в Python преобразует объект даты/времени в строку
            elif isinstance(value, Decimal):   # Decimal - это float в формате str
                value = float(value)
            elif isinstance(value, uuid.UUID): # UUID для работы с универсальными уникальными идентификаторами
                value = str(value)

            # Добавляем значение в результат
            if not exclude_none or value is not None:
                result[column.key] = value

        return result