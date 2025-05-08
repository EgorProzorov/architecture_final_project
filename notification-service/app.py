import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
channel = connection.channel()
channel.queue_declare(queue='notification')

def callback(ch, method, properties, body):
    print("[Notification Service] Received:", body.decode())

channel.basic_consume(queue='notification', on_message_callback=callback, auto_ack=True)
print('[Notification Service] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()