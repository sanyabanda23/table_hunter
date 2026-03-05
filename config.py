import asyncio
import os
from typing import Dict, Any

from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup

from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import Message

from aiogram_dialog import Dialog, Window, setup_dialogs, DialogManager
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.kbd import Checkbox, Button, Row, Cancel, Start


class MainMenu(StatesGroup):
    START = State()


class Settings(StatesGroup):
    START = State()


EXTEND_BTN_ID = "extend"


async def getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    if dialog_manager.find(EXTEND_BTN_ID).is_checked():
        return {
            "extended_str": "on",
            "extended": True,
        }
    else:
        return {
            "extended_str": "off",
            "extended": False,
        }


main_menu = Dialog(
    Window(
        Format(
            "Hello, {event.from_user.username}. \n\n"
            "Extended mode is {extended_str}.\n"
        ),
        Const(
            "Here is some additional text, which is visible only in extended mode",
            when="extended",
        ),
        Row(
            Checkbox(
                checked_text=Const("[x] Extended mode"),
                unchecked_text=Const("[ ] Extended mode"),
                id=EXTEND_BTN_ID,
            ),
            Start(Const("Settings"), id="settings", state=Settings.START),
        ),
        getter=getter,
        state=MainMenu.START
    )
)

NOTIFICATIONS_BTN_ID = "notify"
ADULT_BTN_ID = "adult"

settings = Dialog(
    Window(
        Const("Settings"),
        Checkbox(
            checked_text=Const("[x] Send notifications"),
            unchecked_text=Const("[ ] Send notifications"),
            id=NOTIFICATIONS_BTN_ID,
        ),
        Checkbox(
            checked_text=Const("[x] Adult mode"),
            unchecked_text=Const("[ ] Adult mode"),
            id=ADULT_BTN_ID,
        ),
        Row(
            Cancel(),
            Cancel(text=Const("Save"), id="save"),
        ),
        state=Settings.START,
    )
)

router = Router()


@router.message(CommandStart())
async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MainMenu.START)


async def main():
    bot = Bot(token='Bot Token')
    dp = Dispatcher()
    dp.include_router(main_menu)
    dp.include_router(settings)
    dp.include_router(router)
    setup_dialogs(dp)

    await dp.start_polling(bot)


asyncio.run(main())