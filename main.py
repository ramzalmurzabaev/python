import os
import json
from datetime import datetime
import gspread
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram.ext import CallbackContext

# Указываем путь к вашему файлу с учётными данными
creds = Credentials.from_service_account_file(
    r'C:\Users\adm\Desktop\Bot\pythonProject\credentials.json',
    scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
)

# Подключение к Google API
service = build('drive', 'v3', credentials=creds)

# Указываем ID таблицы
file_id = '1jLTog8z-vw0vEoV2dO6r40x6b7wVHVlb7QSMrAnLKMs'  # Используйте правильный ID

# Добавление доступа для другого пользователя
permission = {
    'type': 'user',
    'role': 'writer',  # Может быть 'writer', если нужно разрешение на редактирование
    'emailAddress': 'murzabaev@edu.surgu.ru'
}

# Запрос на добавление разрешений
try:
    service.permissions().create(fileId=file_id, body=permission).execute()
    print("Доступ для пользователя добавлен успешно.")
except Exception as e:
    print(f"Ошибка при добавлении разрешений: {e}")

# Состояния для ConversationHandler
SELECTING_SERVICE, ENTERING_NAME, ENTERING_BIRTHDAY, ENTERING_SYMPTOMS, ENTERING_ABROAD, ENTERING_ADDRESS, ENTERING_APARTMENT, ENTERING_FLOOR, ENTERING_INTERCOM, ENTERING_PHONE = range(
    10)

# Словарь для хранения данных пользователя
user_data = {}

# Список врачей для вызова на дом
DOCTORS = ["Педиатр", "Терапевт"]

# Google Sheets настройки
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = Credentials.from_service_account_file(r'C:\Users\adm\Desktop\Bot\pythonProject\credentials.json', scopes=SCOPE)
CLIENT = gspread.authorize(CREDS)

# Открытие существующей таблицы по ID
spreadsheet = CLIENT.open_by_key(file_id)  # Используем существующую таблицу по ID
print(f"Таблица '{spreadsheet.title}' открыта.")

# Получаем листы (если они существуют)
try:
    APPLICATIONS_SHEET = spreadsheet.worksheet('Заявки')
    USERS_SHEET = spreadsheet.worksheet('Пользователи')
    ADDRESSES_SHEET = spreadsheet.worksheet('Адреса')
except gspread.exceptions.WorksheetNotFound:
    print("Один или несколько листов не найдены. Создадим их.")
    # Если листы не найдены, создаем их
    APPLICATIONS_SHEET = spreadsheet.add_worksheet(title='Заявки', rows="100", cols="10")
    USERS_SHEET = spreadsheet.add_worksheet(title='Пользователи', rows="100", cols="10")
    ADDRESSES_SHEET = spreadsheet.add_worksheet(title='Адреса', rows="100", cols="10")

# URL для каждой таблицы
spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit"
applications_sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit#gid={APPLICATIONS_SHEET.id}"
users_sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit#gid={USERS_SHEET.id}"
addresses_sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit#gid={ADDRESSES_SHEET.id}"

print(f"Таблица URL: {spreadsheet_url}")
print(f"URL листа 'Заявки': {applications_sheet_url}")
print(f"URL листа 'Пользователи': {users_sheet_url}")
print(f"URL листа 'Адреса': {addresses_sheet_url}")


# Функция для начала общения с ботом
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Здравствуйте! Я помогу вам вызвать врача на дом. Выберите врача:\n"
                                    "1. Педиатр\n"
                                    "2. Терапевт")
    return SELECTING_SERVICE


# Обработка выбора врача
async def select_service(update: Update, context: CallbackContext):
    user_choice = update.message.text
    if user_choice == '1':
        context.user_data['doctor'] = 'Педиатр'
        await update.message.reply_text("Вы выбрали педиатра. Пожалуйста, введите ваше ФИО (фамилия, имя, отчество).")
        return ENTERING_NAME
    elif user_choice == '2':
        context.user_data['doctor'] = 'Терапевт'
        await update.message.reply_text("Вы выбрали терапевта. Пожалуйста, введите ваше ФИО (фамилия, имя, отчество).")
        return ENTERING_NAME
    else:
        await update.message.reply_text("Пожалуйста, выберите 1 для педиатра или 2 для терапевта.")
        return SELECTING_SERVICE


# Получение фамилии, имени, отчества
async def enter_name(update: Update, context: CallbackContext):
    full_name = update.message.text
    context.user_data['full_name'] = full_name
    await update.message.reply_text("Введите вашу дату рождения в формате: ДД.ММ.ГГГГ.")
    return ENTERING_BIRTHDAY


# Проверка и получение даты рождения
async def enter_birthday(update: Update, context: CallbackContext):
    birthday_text = update.message.text
    try:
        birthday = datetime.strptime(birthday_text, "%d.%m.%Y")
        if birthday > datetime.now():
            await update.message.reply_text(
                "Дата рождения не может быть в будущем. Пожалуйста, введите корректную дату.")
            return ENTERING_BIRTHDAY
        context.user_data['birthday'] = birthday
        await update.message.reply_text("Пожалуйста, укажите причину вызова врача или симптомы.")
        return ENTERING_SYMPTOMS
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Пожалуйста, введите дату в формате: ДД.ММ.ГГГГ.")
        return ENTERING_BIRTHDAY


# Получение симптомов
async def enter_symptoms(update: Update, context: CallbackContext):
    symptoms = update.message.text
    context.user_data['symptoms'] = symptoms
    await update.message.reply_text("Были ли вы за границей в последние две недели? (Да/Нет)")
    return ENTERING_ABROAD


# Получение ответа на вопрос о поездках за границу
async def enter_abroad(update: Update, context: CallbackContext):
    abroad = update.message.text
    if abroad.lower() not in ['да', 'нет']:
        await update.message.reply_text("Пожалуйста, ответьте Да или Нет.")
        return ENTERING_ABROAD
    context.user_data['abroad'] = abroad.lower()
    await update.message.reply_text("Пожалуйста, введите ваш адрес проживания (улица, дом, квартира).")
    return ENTERING_ADDRESS


# Получение адреса проживания
async def enter_address(update: Update, context: CallbackContext):
    address = update.message.text
    context.user_data['address'] = address
    await update.message.reply_text("Пожалуйста, укажите ваш подъезд.")
    return ENTERING_APARTMENT


# Получение подъезда
async def enter_apartment(update: Update, context: CallbackContext):
    apartment = update.message.text
    context.user_data['apartment'] = apartment
    await update.message.reply_text("Пожалуйста, укажите ваш этаж.")
    return ENTERING_FLOOR


# Получение этажа
async def enter_floor(update: Update, context: CallbackContext):
    floor = update.message.text
    context.user_data['floor'] = floor
    await update.message.reply_text("Пожалуйста, укажите код домофона.")
    return ENTERING_INTERCOM


# Получение кода домофона
async def enter_intercom(update: Update, context: CallbackContext):
    intercom = update.message.text
    context.user_data['intercom'] = intercom
    await update.message.reply_text("Пожалуйста, введите ваш номер телефона.")
    return ENTERING_PHONE


# Получение номера телефона
async def enter_phone(update: Update, context: CallbackContext):
    phone_number = update.message.text
    context.user_data['phone_number'] = phone_number

    # Формируем данные заявки для сохранения
    user_data_copy = dict(context.user_data)

    # Преобразуем даты в строку перед сохранением
    user_data_copy['birthday'] = user_data_copy['birthday'].strftime('%d.%m.%Y')

    # Сохраняем данные в листы
    APPLICATIONS_SHEET.append_row([user_data_copy['full_name'], user_data_copy['doctor'], user_data_copy['birthday'],
                                   user_data_copy['symptoms'], user_data_copy['abroad'], user_data_copy['phone_number'],
                                   user_data_copy['address'], user_data_copy['apartment'], user_data_copy['floor'],
                                   user_data_copy['intercom']])

    USERS_SHEET.append_row([user_data_copy['full_name'], user_data_copy['phone_number']])

    ADDRESSES_SHEET.append_row([user_data_copy['full_name'], user_data_copy['address']])

    await update.message.reply_text("Ваш запрос принят. Ожидайте звонка, в ближайшее время мы с вами свяжемся для подтверждения записи. Спасибо за использование наших услуг!")
    return ConversationHandler.END


# Запуск бота
def main():
    application = Application.builder().token('7567462248:AAEEPpbcaO0ljHu7YSeP6naXuX0JV8Pntkg').build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_service)],
            ENTERING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            ENTERING_BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_birthday)],
            ENTERING_SYMPTOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_symptoms)],
            ENTERING_ABROAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_abroad)],
            ENTERING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_address)],
            ENTERING_APARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_apartment)],
            ENTERING_FLOOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_floor)],
            ENTERING_INTERCOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_intercom)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone)],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
