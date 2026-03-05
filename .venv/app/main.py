from contextlib import asynccontextmanager
from app.bot.create_bot import dp, start_bot, bot, stop_bot
from app.config import settings, broker, scheduler
from aiogram.types import Update
from fastapi import FastAPI, Request, Response
from loguru import logger
from app.api.router import router as router_fast_stream, disable_booking
import json
import asyncio
import logging
from aiogram import exceptions



@asynccontextmanager                                       # декоратор позволяющий создавать асинхронные контекстные менеджеры на основе генераторных функций
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    logger.info("Бот запущен...")
    await start_bot()
    await broker.start()
    scheduler.start()
    scheduler.add_job(
        disable_booking,                                   # функция‑обработчик, которая будет вызываться по расписанию
        trigger='interval',                                # периодическое выполнение с фиксированным интервалом
        minutes=30,                                        # функция будет запускаться каждые 30 минут
        id='disable_booking_task',                         # Уникальный идентификатор задания
        replace_existing=True                              # Поведение при дубликате: если задание с таким id уже существует, оно будет заменено новым
    )
    webhook_url = settings.hook_url
    await bot.set_webhook(                                 # настраивает веб‑хук — механизм получения обновлений от Telegram через HTTP‑запросы
        url=webhook_url,                                   # полный URL, на который Telegram будет отправлять обновления (сообщения, команды и т. д.)
        allowed_updates=dp.resolve_used_update_types(),    # метод диспетчера (Dispatcher) в aiogram, который автоматически определяет, какие типы обновлений используются в обработчиках бота (например, message, callback_query, inline_query)
        drop_pending_updates=True                          # Telegram удалит все накопившиеся обновления, которые не были обработаны до установки веб‑хука
    )
    logger.success(f"Вебхук установлен: {webhook_url}")
    yield                                                  # превращает обычную функцию в генератор
    logger.info("Бот остановлен...")
    await stop_bot()
    await broker.close()
    scheduler.shutdown()                                   # завершает работу планировщика задач


app = FastAPI(lifespan=lifespan)                           # создаёт экземпляр приложения FastAPI с управлением жизненным циклом через контекстный менеджер lifespan


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    try:
        # Логирование запроса
        logger.info("Получен запрос с вебхука.")
        body = await request.body()
        if not body:
            logger.warning("Пустой запрос.")
            return Response(status_code=400)

        logger.debug(f"Тело запроса: {body.decode()}")

        # Валидация размера
        if len(body) > 1024 * 1024:
            logger.error("Слишком большой запрос.")
            return Response(status_code=413)

        update_data = json.loads(body.decode())
        update = Update.model_validate(update_data, context={"bot": bot})

        # Обработка с таймаутом
        try:
            await asyncio.wait_for(dp.feed_update(bot, update), timeout=10)
            logger.info("Обновление успешно обработано.")
            return Response(status_code=200)
        except asyncio.TimeoutError:
            logger.error("Таймаут при обработке обновления.")
            return Response(status_code=504)

    except json.JSONDecodeError:
        logger.error("Некорректный JSON в запросе.")
        return Response(status_code=400)
    except exceptions.TelegramForbiddenError:
        logger.warning("Бот заблокирован пользователем.")
        return Response(status_code=403)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        return Response(status_code=500)
    


app.include_router(router_fast_stream)