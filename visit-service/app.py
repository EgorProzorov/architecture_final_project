from flask import Flask, jsonify
import redis
import pika

app = Flask(__name__)
redis_client = redis.Redis(host='redis', port=6379)

# Setup RabbitMQ connection
connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
channel = connection.channel()
channel.queue_declare(queue='notification')

@app.route('/visit', methods=['GET'])
def visit():
    count = redis_client.incr('visits')
    channel.basic_publish(exchange='', routing_key='notification', body=f'New visit count: {count}')
    return jsonify({'visit_count': count})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)