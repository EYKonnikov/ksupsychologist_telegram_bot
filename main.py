import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
from questions import QUESTIONS, ANSWER_OPTIONS, calculate_result

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Состояния диалога
START, ANSWERING_QUESTIONS = range(2)
USER_DATA_KEY = "test_data"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    welcome_text = (
   r"🌿 *Здравствуйте, {name}\!* Меня зовут *Ассистент Оксаны* \- Вашего психолога\." + "\n\n"
        r"Вы выбрали возможность пройти *тест Занга* и самостоятельно оценить своё тревожное состояние\. "
        r"Это поможет вам лучше понять текущий уровень вашей тревоги\." + "\n\n"
        
        r"📊 *Что такое шкала Занга?*" + "\n"
        r"_Шкала Занга для самооценки тревоги \(Zung Self\-Rating Anxiety Scale\)_ \- "
        r"это профессиональный инструмент, используемый как вспомогательное средство "
        r"для диагностики тревожных расстройств\." + "\n\n"
        
        r"⚠️ *Обратите внимание:*" + "\n"
        r"— Тест показывает _косвенные признаки_ наличия тревожного расстройства" + "\n"
        r"— Если результаты вызывают сомнения, _обязательно обсудите их со специалистом_" + "\n"
        r"— При указании на возможное расстройство \- _позаботьтесь о себе_ и обратитесь к психологу" + "\n\n"
        
        r"📝 *Инструкция:*" + "\n"
        r"1\. Внимательно прочитайте каждое из 20 утверждений" + "\n"
        r"2\. Выберите ответ, который наиболее соответствует вашему состоянию _за последнюю неделю_" + "\n"
        r"3\. Все ответы обязательны для завершения теста" + "\n\n"
        
        r"👉 Нажмите *«Начать тест»*, чтобы продолжить\."
).format(name=user.first_name)
    await update.message.reply_text(
        welcome_text,
        parse_mode="MarkdownV2",
        reply_markup=ReplyKeyboardMarkup([["Перейти к тесту"]], resize_keyboard=True, one_time_keyboard=True)
    )
    return START

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    buttons = list(ANSWER_OPTIONS.keys())  # Получаем текстовые кнопки
    await update.message.reply_text(
        QUESTIONS[0],
        reply_markup=ReplyKeyboardMarkup(
            [buttons],  # Кнопки: ["1 - Никогда", "2 - Редко", ...]
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    context.user_data[USER_DATA_KEY] = {"current_question": 0, "scores": []}
    return ANSWERING_QUESTIONS

from questions import INVERTED_QUESTIONS  # Добавьте этот импорт

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data.get(USER_DATA_KEY)
    if not user_data:
        await update.message.reply_text("Начните тест с /start")
        return ConversationHandler.END

    text = update.message.text
    if text not in ANSWER_OPTIONS:
        await update.message.reply_text("❌ Выберите вариант из кнопок ниже!")
        return ANSWERING_QUESTIONS

    # Получаем текущий вопрос (индекс начинается с 0)
    current_question_index = user_data["current_question"]
    # Номер вопроса в оригинале (начиная с 1)
    original_question_number = current_question_index + 1

    # Получаем балл и инвертируем, если нужно
    score = ANSWER_OPTIONS[text]
    if original_question_number in INVERTED_QUESTIONS:
        score = 5 - score  # 1 → 4, 2 → 3, 3 → 2, 4 → 1

    user_data["scores"].append(score)
    current_question_index += 1

    if current_question_index < len(QUESTIONS):
        user_data["current_question"] = current_question_index
        await update.message.reply_text(
            QUESTIONS[current_question_index],
            reply_markup=ReplyKeyboardMarkup(
                [list(ANSWER_OPTIONS.keys())],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return ANSWERING_QUESTIONS
    else:
        total_score = sum(user_data["scores"])
        result = calculate_result(total_score)
        await update.message.reply_text(
            result,
           parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.pop(USER_DATA_KEY, None)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Тест отменен.")
    context.user_data.pop(USER_DATA_KEY, None)
    return ConversationHandler.END

def main() -> None:
    app = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_test)],
            ANSWERING_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()