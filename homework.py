import logging
import os
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot  # type: ignore

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    required_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }

    missing_tokens = [
        key for key, value in required_tokens.items() if value is None
    ]
    missing_tokens_string = ', '.join(missing_tokens)

    if missing_tokens:
        raise ValueError(
            f'Отсутствуют необходимые переменные окружения: '
            f'{missing_tokens_string}'
        )
    else:
        print('Все необходимые переменные окружения в наличии.')


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )


def get_api_answer(timestamp):
    """Получает данные от API."""
    request_time = {'from_date': timestamp}
    homework_statuses = requests.get(
        ENDPOINT, headers=HEADERS, params=request_time
    )
    status_response = homework_statuses.status_code

    if status_response != 200:
        raise ValueError(
            f'Ошибка при получении данных от API: '
            f'Статус ответа {status_response}'
        )
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API."""
    required_keys = ['homeworks', 'current_date']

    missing_keys = [key for key in required_keys if key not in response]
    missing_keys_string = ', '.join(missing_keys)

    if missing_keys:
        raise ValueError(
            f'Ответ API не содержит необходимые ключи: '
            f'{missing_keys_string}'
        )
    else:
        print('Ответ API содержит все необходимые ключи.')


def parse_status(homework):
    """Получаю информацию о конкретной домашней работе."""
    homework_name = homework['lesson_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(
            f'Неизвестный статус домашней работы: {homework_status}'
        )
    else:
        verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    # timestamp = int(time.time()) - RETRY_PERIOD
    timestamp = 1725032359

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']

            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)

            timestamp = int(time.time()) - 1

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
