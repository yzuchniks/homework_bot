import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot  # type: ignore

import exceptions as ex

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
TIME_GAP = 1
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def log_and_raise(message, exception, level=logging.ERROR):
    """Логирует сообщение и выбрасывает исключение."""
    logger.log(level, message)
    raise exception(message)


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
        log_and_raise(
            f'Отсутствуют необходимые переменные окружения: '
            f'{missing_tokens_string}',
            ex.MissingTokensError,
            level=logging.CRITICAL
        )
    else:
        logger.debug('Все необходимые переменные окружения в наличии.')


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug('Сообщение успешно отправлено в Telegram.')
    except Exception as error:
        logger.error(f'Сбой при отправке сообщения в Telegram: {error}')


def get_api_answer(timestamp):
    """Получает данные от API."""
    request_time = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=request_time
        )
        status_response = homework_statuses.status_code

        if status_response != 200:
            log_and_raise(
                f'Ошибка при получении данных от API: '
                f'Статус ответа {status_response}',
                ex.ApiRequestError
            )
        return homework_statuses.json()
    except requests.RequestException as error:
        log_and_raise(f'Недоступность эндпоинта: {error}', ex.ApiRequestError)


def check_response(response):
    """Проверяет ответ API."""
    if not isinstance(response, dict):
        log_and_raise(
            'Структура ответа API не является словарем.',
            TypeError
        )

    required_keys = ['homeworks', 'current_date']
    missing_keys = [key for key in required_keys if key not in response]
    missing_keys_string = ', '.join(missing_keys)

    if missing_keys:
        log_and_raise(
            f'Ответ API не содержит необходимые ключи: '
            f'{missing_keys_string}',
            KeyError
        )
    if not isinstance(response['homeworks'], list):
        log_and_raise(
            'Данные под ключом "homeworks" не являются списком.',
            TypeError
        )

    logger.debug('Ответ API содержит все необходимые ключи.')


def parse_status(homework):
    """Получаю информацию о конкретной домашней работе."""
    if 'homework_name' not in homework:
        log_and_raise(
            'Ответ API не содержит ключ "homework_name".',
            ex.HomeworkStatusError
        )
    homework_name = homework['homework_name']
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        log_and_raise(
            f'Неизвестный статус домашней работы: {homework_status}',
            ex.HomeworkStatusError
        )
    else:
        verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    # timestamp = 1725032359

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']

            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Отсутствие в ответе новых статусов.')

            timestamp = int(time.time()) - TIME_GAP

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
