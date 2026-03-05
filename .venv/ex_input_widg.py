from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager, StartMode, setup_dialogs
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.text import Const, Format


# 1. Состояния диалога
class FormSG(StatesGroup):
    name = State()      # Шаг 1: ввод имени
    age = State()       # Шаг 2: ввод возраста
    confirm = State()   # Шаг 3: подтверждение данных

# 2. Обработчики ввода
async def on_name_input(message: Message, dialog: Dialog, manager: DialogManager):
    manager.dialog_data["name"] = message.text
    await manager.next()  # переходим к состоянию age

async def on_age_input(message: Message, dialog: Dialog, manager: DialogManager):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    manager.dialog_data["age"] = int(message.text)
    await manager.next()  # переходим к confirm

# 3. Окна диалога
name_window = Window(
    Const("Как вас зовут?"),
    MessageInput(on_name_input),
    state=FormSG.name
)

age_window = Window(
    Const("Сколько вам лет?"),
    MessageInput(on_age_input),
    state=FormSG.age
)

confirm_window = Window(
    Format("Ваше имя: {dialog_data[name]}, возраст: {dialog_data[age]}. Всё верно?"),
    Const("Напишите «да» для подтверждения."),
    MessageInput(lambda msg, dialog, manager: manager.done()),
    state=FormSG.confirm
)

# 4. Создание диалога
dialog = Dialog(name_window, age_window, confirm_window)

# 5. Настройка бота и диспетчера
storage = MemoryStorage()
bot = Bot(token="8136688435:AAEZw7L8ksQDFZn5XWunyDVhRMLU3oDUq1A")
dp = Dispatcher(storage=storage)

# 6. Регистрация диалога
dp.include_router(dialog)
setup_dialogs(dp)

# 7. Хэндлер для /start
@dp.message(Command("start"))
async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(FormSG.name, mode=StartMode.RESET_STACK)

# 8. Запуск бота
if __name__ == "__main__":
    dp.run_polling(bot, skip_updates=True)