class MissingTokensError(Exception):
    """Отсутствие нужных ключей или токенов."""


class ApiRequestError(Exception):
    """Ошибка при получении данных от API."""


class HomeworkStatusError(KeyError):
    """Статус домашней работы не соответствует ожидаемому."""
