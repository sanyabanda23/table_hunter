from datetime import datetime, timedelta
from faststream.rabbit.fastapi import RabbitRouter
from loguru import logger
from app.bot.create_bot import bot
from app.config import settings, scheduler
from app.dao.dao import BookingDAO
from app.dao.database import async_session_maker

router = RabbitRouter(url=settings.rabbitmq_url)

@router.subscriber("admin_msg")                     # декоратор подписывает функцию на очередь сообщений admin_msg
async def send_booking_msg(msg: str):
    for admin in settings.ADMIN_IDS:
        await bot.send_message(admin, text=msg)

async def send_user_msg(user_id: int, text: str):
    await bot.send_message(user_id, text=text)

@router.subscriber("noti_user")
async def schedule_user_notifications(user_id: int):
    """Планирует отправку серии сообщений пользователю с разными интервалами."""
    now = datetime.now()

    notifications = [
        {
            "time": now + timedelta(hours=1),
            "text": "Спасибо за выбор нашего ресторана! Мы надеемся, вам понравится. "
                    "Оставьте отзыв, чтобы мы стали лучше! 😊",
        },
        {
            "time": now + timedelta(hours=3),
            "text": "Не хотите забронировать столик снова? Попробуйте наше новое меню! 🍽️",
        },
        {
            "time": now + timedelta(hours=12),
            "text": "Специально для вас! Скидка 10% на следующее посещение по промокоду WELCOMEBACK. 🎉",
        },
        {
            "time": now + timedelta(hours=24),
            "text": "Мы ценим ваше мнение! Расскажите о своем опыте и получите приятный бонус! 🎁",
        },
    ]

    for i, notification in enumerate(notifications):
        job_id = f"user_notification_{user_id}_{i}"
        scheduler.add_job(
            send_user_msg,                           # функция, которая будет вызвана
            "date",                                  # тип задания: однократное выполнение в указанную дату
            run_date=notification["time"],           # точная дата/время выполнения
            args=[user_id, notification["text"]],    # аргументы для функции
            id=job_id,                               # уникальный идентификатор задания
            replace_existing=True,                   # заменить существующее задание с таким же id
        )
        logger.info(
            f"Запланировано уведомление для пользователя {user_id} на {notification['time']}"
        )

async def disable_booking():
    async with async_session_maker() as session:
        await BookingDAO(session).complete_past_bookings()