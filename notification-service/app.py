import pika
import time
from prometheus_client import start_http_server, Counter

RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_QUEUE = 'notification'
LOG_FILE = 'received_messages.log'

# Определяем метрику
MESSAGES_RECEIVED = Counter('messages_received', 'Number of messages received')

def connect_with_retry():
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            return connection
        except pika.exceptions.AMQPConnectionError:
            print(" [!] Не удалось подключиться к RabbitMQ. Повтор через 3 сек...")
            time.sleep(3)

def log_message(message):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {message}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

def callback(ch, method, properties, body):
    try:
        message = body.decode()
        print(f"Received: {message}")
        log_message(message)
        MESSAGES_RECEIVED.inc()  # Увеличиваем счётчик полученных сообщений
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    connection = connect_with_retry()
    channel = connection.channel()

    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback, auto_ack=False)

    print('[*] Ожидание сообщений...')
    channel.start_consuming()

if __name__ == '__main__':
    start_http_server(8000)  # Запускаем HTTP-сервер для экспорта метрик
    main()