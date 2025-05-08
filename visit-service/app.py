from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import redis
import pika
import requests
import json
import uvicorn
import time
from datetime import timedelta

app = FastAPI()

# Redis client
redis_client = redis.Redis(host='redis', port=6379)

def connect_to_rabbitmq():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("[Notification Service] Waiting for RabbitMQ...")
            time.sleep(5)

# RabbitMQ connection
connection = connect_to_rabbitmq()
channel = connection.channel()
channel.queue_declare(queue='notification')

# OpenWeatherMap API configuration
WEATHER_API_KEY = '8ef8cc382a2f77924bf9720e58eb303f'
WEATHER_API_URL = 'http://api.openweathermap.org/data/2.5/weather'


@app.get("/visit")
def visit():
    """Increment visit count and send notification."""
    count = redis_client.incr('visits')
    channel.basic_publish(exchange='', routing_key='notification', body=f'New visit count: {count}')
    return {"visit_count": count}


@app.get("/weather")
def weather(city: str = Query(..., description="City name to get the weather for")):
    """Get weather for a city, with caching."""
    # Check cache
    cache_key = f'weather:{city.lower()}'
    cached_weather = redis_client.get(cache_key)
    if cached_weather:
        return {"source": "cache", "data": json.loads(cached_weather)}

    # Fetch weather from API
    try:
        response = requests.get(WEATHER_API_URL, params={
            'q': city,
            'appid': WEATHER_API_KEY,
            'units': 'metric'
        })
        response.raise_for_status()
        weather_data = response.json()

        # Cache the response for 1 hour
        redis_client.setex(cache_key, timedelta(hours=1), json.dumps(weather_data))

        return {"source": "api", "data": weather_data}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather data: {str(e)}")
        


# Run the application
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)