import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import aiohttp
from models import Contact, MessageRequest, SupervisorModel

API_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEBAPP_URL")
CONTACT_SERVICE_URL = os.getenv("CONTACT_SERVICE_URL")
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(Command(commands=["start"]))
async def start_handler(message: Message):
    button = InlineKeyboardButton(text="Wallet", web_app=WebAppInfo(url=WEB_APP_URL))
    markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
    await message.answer(
        (
            "Добро пожаловать! Чтобы подключить свой кошелек, нажмите на кнопку Wallet ниже.\n"
            "Вы можете также добавить контакт, используя команду /add_contact <имя> <wallet_public_key>.\n"
            "После этого вы сможете отправлять транзакции, просто написав 'отправь маме 100 ETH', "
            "а также спрашивать меня о блокчейне.\n"
        ),
        reply_markup=markup,
    )


@dp.message(Command(commands=["add_contact"]))
async def add_contact_handler(message: Message):
    # 0x71d97dA16Dcc0c85F028B8Fd359a81DDF885DE59
    tokens = message.text.split()
    if len(tokens) < 3:
        await message.reply("Использование: /add_contact <имя> [фамилия] <wallet_public_key>")
        return
    public_key = tokens[-1]
    name = " ".join(tokens[1:-1])

    contact = Contact(
        user_tg_id=str(message.from_user.id),
        contact_name=name,
        wallet_id=public_key,
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(CONTACT_SERVICE_URL + "/contacts/add", json=contact.model_dump()) as resp:
            await resp.text()

    await message.reply(f"Контакт {name} добавлен.")


@dp.message()
async def message_handler(message: Message):
    text = message.text.strip()

    message_request = MessageRequest(message=text, user_tg_id=message.from_user.id)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            AGENT_SERVICE_URL + "/api/call_agent",
            params=message_request.model_dump(),
        ) as response:
            response = await response.json()
            response = SupervisorModel.model_validate(response)

    if response.tx is not None:
        tx = response.tx
        query = f"?to={tx.transaction.to}&value={tx.transaction.value}&token={tx.transaction.currency}"
        button = InlineKeyboardButton(
            text="Подтвердить транзакцию",
            web_app=WebAppInfo(url=WEB_APP_URL + "/transaction" + query),
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
        await message.answer("Подтвердите транзакцию:", reply_markup=markup)
    elif response.small_talk is not None:
        await message.reply(response.small_talk.response)
    elif response.off_topic is not None:
        await message.reply(response.off_topic.response)
    elif response.rag_response is not None:
        await message.reply(response.rag_response.answer)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
