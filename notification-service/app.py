import pika
import time

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

def callback(ch, method, properties, body):
    print("[Notification Service] Received:", body.decode())

channel.basic_consume(queue='notification', on_message_callback=callback, auto_ack=True)
print('[Notification Service] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()