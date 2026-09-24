import os
import logging
from fastapi import FastAPI, Request
import requests

# Настройка логирования, чтобы видеть всё в логах Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 1. ИСПРАВЛЕНО: используем "прямой" URL из вашего конфига
DEEPSEEK_API_URL = "https://direct.router-cheap.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 2. ИСПРАВЛЕНО: выбрана быстрая модель (без "thinking"), чтобы уложиться в лимит Алисы 4.5 сек
# Можно заменить на "deepseek-v4-pro" или "gpt-5.4-mini" при необходимости
MODEL_NAME = "deepseek-v4-flash"


@app.post("/")
async def main(request: Request):
    body = await request.json()
    user_text = body["request"]["original_utterance"]

    # Логируем входящий запрос от Алисы
    logger.info(f"User said: {user_text}")

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": user_text}],
            },
            timeout=7,  # 3. ДОБАВЛЕНО: таймаут, чтобы не превысить лимит Алисы
        )

        # 4. ДОБАВЛЕНО: логируем полный ответ от роутера — это ключ к отладке
        logger.info(f"Router status: {response.status_code}")
        logger.info(f"Router raw response: {response.text}")

        response_data = response.json()

        # 5. ИСПРАВЛЕНО: безопасное извлечение ответа вместо падения с KeyError
        if "choices" in response_data and len(response_data["choices"]) > 0:
            answer = response_data["choices"][0]["message"]["content"]
        else:
            # Логируем ошибку от роутера и возвращаем понятный текст
            logger.error(f"Unexpected response from router: {response_data}")
            error_message = response_data.get("error", {}).get("message", "Неизвестная ошибка")
            answer = f"Извините, произошла ошибка при получении ответа. {error_message}"

    except requests.exceptions.Timeout:
        logger.error("Request to router timed out")
        answer = "Извините, я не успел подумать. Попробуйте ещё раз."
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        answer = "Извините, произошла внутренняя ошибка."

    return {
        "version": body["version"],
        "session": body["session"],
        "response": {
            "end_session": False,
            "text": answer
        }
    }
