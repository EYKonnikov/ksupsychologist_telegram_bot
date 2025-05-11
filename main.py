
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


        


async def finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Добавляем отладочный вывод
    print("[DEBUG] Завершение теста. Отправка кнопок...")
    
    try:
        total_score = sum(context.user_data["test_data"]["scores"])
        result = calculate_result(total_score)
        
        # Создаем клавиатуру
        keyboard = ReplyKeyboardMarkup(
            [["🏠 Главное меню", "🔄 Повторить тест"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        print(f"[DEBUG] Создана клавиатура: {keyboard.to_dict()}")

        # Отправляем сообщение с клавиатурой
        await update.message.reply_text(
            f"Тест завершен!\n\n{result}",
            reply_markup=keyboard
        )
        
    except KeyError as e:
        print(f"[ERROR] Ошибка в finish_test: {e}")
        await update.message.reply_text("Ошибка обработки результатов")
    
    # Очищаем данные
    context.user_data.pop("test_data", None)
    return MAIN_MENU

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ответы пользователя на вопросы теста"""
    try:
        # 1. Получаем данные теста
        user_data = context.user_data.get("test_data")
        
        # 2. Проверяем инициализацию теста
        if not user_data:
            await update.message.reply_text("❌ Тест не был начат. Используйте /start")
            return ConversationHandler.END

        # 3. Получаем текущий индекс вопроса
        current_question_idx = user_data["current_question"]
        print(f"[DEBUG] Текущий вопрос: {current_question_idx + 1}/{len(QUESTIONS)}")

        # 4. Обрабатываем ответ
        answer_text = update.message.text
        if answer_text not in ANSWER_OPTIONS:
            raise KeyError("Некорректный ответ")

        # 5. Рассчитываем баллы
        score = ANSWER_OPTIONS[answer_text]
        
        # 6. Инвертируем баллы для специальных вопросов
        if (current_question_idx + 1) in INVERTED_QUESTIONS:
            score = 5 - score
            print(f"[DEBUG] Инвертированный балл: {score}")

        # 7. Сохраняем результат
        user_data["scores"].append(score)
        user_data["current_question"] += 1

        # 8. Проверяем завершение теста
        if user_data["current_question"] >= len(QUESTIONS):
            print("[DEBUG] Все вопросы пройдены")
            return await finish_test(update, context)

        # 9. Отправляем следующий вопрос
        next_question_idx = user_data["current_question"]
        await update.message.reply_text(
            QUESTIONS[next_question_idx],
            reply_markup=ReplyKeyboardMarkup(
                [[btn] for btn in ANSWER_OPTIONS.keys()],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return TEST_IN_PROGRESS

    except KeyError:
        # 10. Обработка некорректного ответа
        error_message = (
            "⚠️ Пожалуйста, используйте кнопки для ответа!\n"
            f"Доступные варианты: {', '.join(ANSWER_OPTIONS.keys())}"
        )
        await update.message.reply_text(error_message)
        return TEST_IN_PROGRESS

    except Exception as e:
        # 11. Общая обработка ошибок
        print(f"[ERROR] Ошибка в handle_answer: {str(e)}")
        await update.message.reply_text("🚨 Произошла ошибка. Пожалуйста, начните тест заново.")
        return ConversationHandler.END

async def handle_main_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "🏠 Главное меню":
        await show_main_menu(update, context)
        return MAIN_MENU
    elif text == "🔄 Повторить тест":
        # Очищаем предыдущие данные теста
        context.user_data.pop("test_data", None)
        return await start_test(update, context)
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог прерван", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def return_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await show_main_menu(update, context)
    return MAIN_MENU

def main() -> None:
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                # Обработчик для кнопок "🏠 Главное меню" и "🔄 Повторить тест"
                MessageHandler(
                    filters.Regex(r"^(🏠 Главное меню|🔄 Повторить тест)$"),
                    handle_main_menu_buttons
                ),
                # Общий обработчик для других кнопок
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
            ],
            TEST_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_test)],
            TEST_IN_PROGRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    app.add_error_handler(error_handler)
    app.add_handler(conv_handler)
    app.run_polling()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"[ERROR] Ошибка: {context.error}")
    if update.message:
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте снова.")

if __name__ == "__main__":
    main()

