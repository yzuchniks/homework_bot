class MissingTokensError(Exception):
    """Отсутствие нужных ключей или токенов."""

    pass


class ApiRequestError(Exception):
    """Ошибка при получении данных от API."""

    pass


class HomeworkStatusError(Exception):
    """Статус домашней работы не соответствует ожидаемому."""

    pass
