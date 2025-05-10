import pika
import time

RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_QUEUE = 'notification'

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

def callback(ch, method, properties, body):
    try:
        print(f"Received: {body.decode()}")
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
    main()
