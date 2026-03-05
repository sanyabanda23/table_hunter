import os
from typing import List
from urllib.parse import quote
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore #компонент библиотеки APScheduler, позволяющий сохранять запланированные задачи в реляционной базе данных через SQLAlchemy
from apscheduler.schedulers.asyncio import AsyncIOScheduler  #предназначенный для асинхронного планирования задач в приложениях на базе asyncio
from faststream.rabbit import RabbitBroker
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int]
    INIT_DB: bool
    FORMAT_LOG: str = "{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}"
    LOG_ROTATION: str = "10 MB"
    DB_URL: str = 'sqlite+aiosqlite:///data/db.sqlite3' 
    STORE_URL: str = 'sqlite:///data/jobs.sqlite'
    TABLES_JSON: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dao", "tables.json")
    SLOTS_JSON: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dao", "slots.json")

    BASE_URL: str
    RABBITMQ_USERNAME: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    VHOST: str

    @property # Определяет геттер — метод, возвращающий значение атрибута.
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USERNAME}:{quote(self.RABBITMQ_PASSWORD)}@"
            f"{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.VHOST}"
        )

    @property
    def hook_url(self) -> str:
        """Возвращает URL вебхука"""
        return f"{self.BASE_URL}/webhook"

    # определяет, откуда и как Pydantic будет загружать настройки приложения
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    ) 


# Инициализация конфигурации
settings = Settings()

# Настройка логирования
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")
logger.add(log_file_path, format=settings.FORMAT_LOG, level="INFO", rotation=settings.LOG_ROTATION) # Файл логов log.txt создается автоматически, а Loguru позволяет удобно управлять логами, включая их ротацию

# Создание брокера сообщений RabbitMQ
broker = RabbitBroker(url=settings.rabbitmq_url)

# Создание планировщика задач
scheduler = AsyncIOScheduler(jobstores={'default': SQLAlchemyJobStore(url=settings.STORE_URL)})