import requests
import json
import uvicorn
import time
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Query
import redis
import pika
from prometheus_client import start_http_server, Counter, Histogram

app = FastAPI()

redis_client = redis.Redis(host='redis', port=6379)

# Определяем метрики
VISIT_COUNT = Counter('visit_count', 'Number of visits')
WEATHER_REQUEST_COUNT = Counter('weather_request_count', 'Number of weather requests')
WEATHER_REQUEST_LATENCY = Histogram('weather_request_latency_seconds', 'Weather request latency')

def connect_to_rabbitmq():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', heartbeat=10))
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("[Notification Service] Waiting for RabbitMQ...")
            time.sleep(5)

WEATHER_API_KEY = '8ef8cc382a2f77924bf9720e58eb303f'
WEATHER_API_URL = 'http://api.openweathermap.org/data/2.5/weather'

@app.get("/visit")
def visit():
    """Increment visit count and send notification."""
    count = redis_client.incr('visits')
    VISIT_COUNT.inc()  # Увеличиваем счётчик посещений

    try:
        connection = connect_to_rabbitmq()
        channel = connection.channel()
        channel.queue_declare(queue='notification', durable=True)
        channel.basic_publish(exchange='', routing_key='notification', body=f'New visit count: {count}')
    except pika.exceptions.AMQPConnectionError as e:
        # Логируем ошибку и возвращаем сообщение об ошибке
        print(f"[Notification Service] Failed to send message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message to RabbitMQ.")
    return {"visit_count": count}

@app.get("/weather")
def weather(city: str = Query(..., description="City name to get the weather for")):
    """Get weather for a city, with caching."""
    WEATHER_REQUEST_COUNT.inc()  # Увеличиваем счётчик запросов погоды
    start_time = time.time()
    try:
        connection = connect_to_rabbitmq()
        channel = connection.channel()
        channel.queue_declare(queue='notification', durable=True)

        cache_key = f'weather:{city.lower()}'
        cached_weather = redis_client.get(cache_key)
        if cached_weather:
            channel.basic_publish(exchange='', routing_key='notification', body=f"Weather data for {city} retrieved from cache.")
            return {"source": "cache", "data": json.loads(cached_weather)}

        response = requests.get(WEATHER_API_URL, params={
            'q': city,
            'appid': WEATHER_API_KEY,
            'units': 'metric'
        })
        response.raise_for_status()
        weather_data = response.json()

        redis_client.setex(cache_key, timedelta(hours=1), json.dumps(weather_data))
        channel.basic_publish(exchange='', routing_key='notification', body=f"Weather data for {city} retrieved from API.")

        return {"source": "api", "data": weather_data}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather data: {str(e)}")
    finally:
        end_time = time.time()
        WEATHER_REQUEST_LATENCY.observe(end_time - start_time)  # Измеряем задержку

if __name__ == "__main__":
    start_http_server(8001)  # Запускаем HTTP-сервер для экспорта метрик
    uvicorn.run(app, host="0.0.0.0", port=5001)