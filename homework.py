import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot  # type: ignore
from telebot.apihelper import ApiException  # type: ignore

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

log_filename = os.path.basename(__file__) + '.log'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
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
    except ApiException as api_error:
        logger.exception(f'Ошибка API Telegram: {api_error}')
        return False
    except requests.RequestException as request_error:
        logger.exception(f'Ошибка запроса к Telegram: {request_error}')
        return False
    except Exception as error:
        logger.exception(f'Сбой при отправке сообщения в Telegram: {error}')
        return False
    else:
        logger.debug('Сообщение успешно отправлено в Telegram.')
        return True


def get_api_answer(timestamp):
    """Получает данные от API."""
    request_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        response = requests.get(**request_params)
    except requests.RequestException as error:
        log_and_raise(
            f'Недоступность эндпоинта: {error}. '
            f'Параметры запроса: {request_params}',
            ex.ApiRequestError
        )
    status_response = response.status_code
    if status_response != HTTPStatus.OK:
        log_and_raise(
            f'Ошибка при получении данных от API: '
            f'Статус ответа {status_response}. '
            f'Параметры запроса: {request_params}',
            ex.ApiRequestError
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API."""
    if not isinstance(response, dict):
        type_response = type(response)
        log_and_raise(
            f'Структура ответа API не соответсвует ожидаемой. '
            f'Полученный тип данных: {type_response}.',
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
        type_homeworks = type(response['homeworks'])
        log_and_raise(
            f'Тип данных под ключом "homeworks" не соответсвует ожидаемому. '
            f'Полученный тип данных: {type_homeworks}.',
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
    error_reported = False

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if homeworks:
                message = parse_status(homeworks[0])
                success = send_message(bot, message)
                if not success:
                    logger.warning(
                        'Не удалось отправить сообщение в Telegram.'
                        'Повторная попытка через 60 секунд.'
                    )
                    time.sleep(60)
                    continue
            else:
                logger.debug('Отсутствие в ответе новых статусов.')

            timestamp = int(time.time()) - TIME_GAP
            error_reported = False
        except Exception as error:
            logger.exception(f'Сбой в работе программы: {error}')
            if not error_reported:
                error_message = f'Ошибка в работе программы: {error}'
                send_message(bot, error_message)
                error_reported = True

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
