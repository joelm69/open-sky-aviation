from kafka import KafkaConsumer


consumer = KafkaConsumer(
    "aircraft-states",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest",
    consumer_timeout_ms=5000,
)

for message in consumer:
    print("Message value:")
    print(repr(message.value))
    print("Message size:", len(message.value))
    break

consumer.close()