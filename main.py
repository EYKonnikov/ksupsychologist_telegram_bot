
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from questions import QUESTIONS, ANSWER_OPTIONS, calculate_result, INVERTED_QUESTIONS  # Импорт существующего теста
load_dotenv()
# Состояния диалога
MAIN_MENU, TEST_SELECTION, TEST_IN_PROGRESS = range(3)

# Текстовые константы
MAIN_MENU_TEXT = (
    "<b>✨ Бот-Ассистент Оксаны ✨</b>\n\n"
       "<i>Доброго времени суток!</i>\n"
       "Добро пожаловать в надёжные руки ассистента Оксаны - Вашего психолога.\n\n"
       "Здесь Вы можете найти полезные материалы из мира психологии, которые постоянно пополняются.\n\n"
       "👇 <b>Выберите раздел:</b>"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await show_main_menu(update, context)
    return MAIN_MENU

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    menu_buttons = [["🧪 Тесты", "🏃 Марафоны"], ["💪 Тренажёры", "📞 Контакты"]]
    await update.message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=ReplyKeyboardMarkup(menu_buttons, resize_keyboard=True),
        parse_mode="HTML"
    )

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "🧪 Тесты":
        await show_test_selection(update, context)
        return TEST_SELECTION
    elif text == "💪 Тренажёры":
        await update.message.reply_text("Раздел в разработке 🛠")
        return MAIN_MENU
    # Обработка других кнопок
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки меню")
        return MAIN_MENU

async def show_test_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    test_buttons = [["Шкала Занга (Тревога)"], ["🔙 Назад"]]
    await update.message.reply_text(
        "📚 *Доступные тесты:*\nВыберите тест для прохождения:",
        reply_markup=ReplyKeyboardMarkup(test_buttons, resize_keyboard=True),
        parse_mode="MarkdownV2"
    )

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["test_data"] = {
        "current_question": 0,  # Индексы начинаются с 0
        "scores": []
    }
    print("[DEBUG] Тест начат. Вопросов в базе:", len(QUESTIONS))
    await update.message.reply_text(
        QUESTIONS[0],  # Первый вопрос
        reply_markup=ReplyKeyboardMarkup([[btn] for btn in ANSWER_OPTIONS.keys()], resize_keyboard=True)
    )
    return TEST_IN_PROGRESS

async def send_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    test_data = context.user_data["test_data"]
    current_question = test_data["current_question"]
    
    if current_question < len(QUESTIONS):
        await update.message.reply_text(
            QUESTIONS[current_question],
            reply_markup=ReplyKeyboardMarkup(
                [[btn] for btn in ANSWER_OPTIONS.keys()], 
                resize_keyboard=True
            )
        )
        return TEST_IN_PROGRESS
    else:
        return await finish_test(update, context)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data.get("test_data")
    print(f"[DEBUG] Текущий вопрос: {user_data['current_question'] + 1}")
    if not user_data:
        await update.message.reply_text("❌ Тест не начат. Используйте /start")
        return ConversationHandler.END

    current_question_idx = user_data["current_question"]
    
    try:
        answer = update.message.text
        score = ANSWER_OPTIONS[answer]
        
        # Инвертирование баллов для определенных вопросов
        if (current_question_idx + 1) in INVERTED_QUESTIONS:  # +1, так как вопросы нумеруются с 1
            score = 5 - score
            
        user_data["scores"].append(score)
        user_data["current_question"] += 1  # Увеличиваем индекс
        
    except KeyError:
        await update.message.reply_text("❌ Выберите вариант из кнопок!")
        return TEST_IN_PROGRESS

    # Проверяем, остались ли вопросы
    if user_data["current_question"] < len(QUESTIONS):
        await update.message.reply_text(
            QUESTIONS[user_data["current_question"]],  # Следующий вопрос
            reply_markup=ReplyKeyboardMarkup([[btn] for btn in ANSWER_OPTIONS.keys()], resize_keyboard=True)
        )
        return TEST_IN_PROGRESS
    else:
        total_score = sum(user_data["scores"])
        result = calculate_result(total_score)
        await update.message.reply_text(result, parse_mode="MarkdownV2")
        context.user_data.pop("test_data", None)
        return ConversationHandler.END
        
async def handle_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Существующая логика обработки ответов
    # ...
    return await send_next_question(update, context)

async def finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Логика завершения теста
    await show_main_menu(update, context)
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог прерван", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

def main() -> None:
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
     entry_points=[CommandHandler("start", start)],
     states={
         MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
         TEST_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_test)],
         TEST_IN_PROGRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]  # Важно!
     },
     fallbacks=[CommandHandler("cancel", cancel)],
     allow_reentry=True
 )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()

