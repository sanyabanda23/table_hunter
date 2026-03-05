from aiogram import F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.router import Router
from aiogram_dialog import DialogManager, StartMode
from pydantic import create_model
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.booking.state import BookingState
from app.bot.user.kbs import main_user_kb, user_booking_kb, cancel_book_kb
from app.bot.user.schemas import SUser
from app.config import broker
from app.dao.dao import UserDAO, BookingDAO

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session_with_commit: AsyncSession, state: FSMContext):
    await state.clear()
    user_data = message.from_user
    user_id = user_data.id
    user_info = await UserDAO(session_with_commit).find_one_or_none_by_id(user_id)
    if user_info is None:
        user_schema = SUser(id=user_id, first_name=user_data.first_name,
                            last_name=user_data.last_name, username=user_data.username)
        await UserDAO(session_with_commit).add(user_schema)
    text = ("👋 Добро пожаловать в Binary Bites! 🍽️\n\nЗдесь каждый байт вкуса закодирован в удовольствие. 😋💻\n"
            "Используйте клавиатуру ниже, чтобы зарезервировать свой столик и избежать переполнения буфера! 🔢🍴")
    await message.answer(text, reply_markup=main_user_kb(user_id))


@router.callback_query(F.data == "about_us")
async def cmd_about(call: CallbackQuery):
    await call.answer("О нас")
    about_text = ("🖥️ О Binary Bites 🍔\n\n"
                  "Мы - первый ресторан, где кулинария встречается с кодом! 👨‍💻👩‍💻\n\n"
                  "🍽️ Наше меню - это настоящий алгоритм вкуса:\n\n"
                  "• Закуски начинаются с 'Hello World' салата 🥗\n"
                  "• Основные блюда включают 'Full Stack' бургер 🍔\n"
                  "• Не забудьте про наш фирменный 'Python' кофе ☕\n\n"
                  "🏆 Наша миссия - оптимизировать ваше гастрономическое удовольствие!\n\n"
                  "📍 Мы находимся по адресу: ул. Программная, д. 404\n"
                  "🕐 Работаем 24/7, потому что настоящие разработчики не спят😉\n\n"
                  "Приходите к нам, чтобы отладить свой аппетит! 🍽️💻")
    await call.message.edit_text(about_text, reply_markup=main_user_kb(call.from_user.id))

@router.callback_query(F.data == "my_bookings")
async def show_my_bookings(call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer("Мои брони")
    user_filter = create_model(                                                        # динамическое создание и инстанцирование Pydantic‑модели
        'UserIDModel',                                                                 # название модели
        user_id=(int, ...)                                                             # поле user_id типа int с валидацией (многоточие ... означает «обязательное поле») 
        )(user_id=call.from_user.id)                                                   # модель с переданным значением user_id
    my_bookings = await BookingDAO(session_without_commit).find_all(user_filter)
    count_booking = len(my_bookings)
    if count_booking:
        book = True
        text = (f"🎉 Отлично! У вас {count_booking} забронированных столика(ов). \n\n"
                f"Чтобы просмотреть детали брони и, при необходимости, отменить бронь, воспользуйтесь кнопками ниже. 👇")
    else:
        book = False
        text = ("🤔 Кажется, у вас пока нет активных бронирований. \n\n"
                f"Не проблема!  Вы можете забронировать столик прямо сейчас, нажав на кнопку ниже. 😉👇")
    await call.message.edit_text(text, reply_markup=user_booking_kb(call.from_user.id, book))


@router.callback_query(F.data == "my_booking_all")
async def show_all_my_bookings(call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer("Все мои брони")
    user_bookings = await BookingDAO(session_without_commit).get_bookings_with_details(call.from_user.id)

    if not user_bookings:
        await call.message.edit_text("😔 У вас пока нет активных бронирований.", reply_markup=None)
        return

    for i, book in enumerate(user_bookings):                                          # enumerate(user_bookings) в Python преобразует итерируемый объект в итератор пар «индекс — элемент»
        # Форматируем дату и время для удобства чтения
        booking_date = book.date.strftime("%d.%m.%Y")  # День.Месяц.Год
        start_time = book.time_slot.start_time
        end_time = book.time_slot.end_time
        booking_number = i + 1
        status = book.status
        cancel = False
        home_page = False
        if status == "booked":
            cancel = True
            status_text = "Забронирован"
        elif status == "canceled":
            status_text = "Отменен"
        else:
            status_text = "Завершен"
        message_text = (f"<b>Бронь №{booking_number}:</b>\n\n"
                        f"📅 <b>Дата:</b> {booking_date}\n"
                        f"🕒 <b>Время:</b> {start_time} - {end_time}\n"
                        f"🪑 <b>Столик:</b> №{book.table.id}, Вместимость: {book.table.capacity}\n"
                        f"ℹ️ <b>Описание:</b> {book.table.description}\n"
                        f"📌 <b>Статус:</b> {status_text}\n\n")
        if booking_number == len(user_bookings):
            home_page = True
        await call.message.answer(message_text, reply_markup=cancel_book_kb(book.id, cancel, home_page))


@router.callback_query(F.data.startswith("cancel_book_"))
async def cancel_booking(call: CallbackQuery, session_with_commit: AsyncSession):
    book_id = int(call.data.split("_")[-1])
    booking_dao = BookingDAO(session_with_commit)
    await booking_dao.cancel_book(book_id)
    await call.answer("Бронь отменена!", show_alert=True)
    await broker.publish(f"Пользователь отменил запись о брони с ID {book_id}", "admin_msg")
    await call.message.edit_reply_markup(reply_markup=cancel_book_kb(book_id))


@router.callback_query(F.data.startswith("dell_book_"))
async def delete_booking(call: CallbackQuery, session_with_commit: AsyncSession):
    book_id = int(call.data.split("_")[-1])
    await BookingDAO(session_with_commit).delete_book(book_id)
    await call.answer("Запись о брони удалена!", show_alert=True)
    await broker.publish(f"Пользователь удалил запись о брони с ID {book_id}", "admin_msg")
    await call.message.delete()        # Асинхронный метод, отправляющий запрос к API Telegram на удаление сообщения

@router.callback_query(F.data == "book_table")
async def start_dialog(call: CallbackQuery, dialog_manager: DialogManager):
    await call.answer("Бронирование столика")
    await dialog_manager.start(state=BookingState.count, mode=StartMode.RESET_STACK) # StartMode.RESET_STACK режим запуска диалога, где полностью очищается текущий стек диалогов перед запуском нового

@router.callback_query(F.data == "back_home")
async def delete_booking(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer('Главное меню', reply_markup=main_user_kb(call.from_user.id))