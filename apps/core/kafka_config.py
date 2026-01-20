from kafka import KafkaProducer, KafkaConsumer
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

class KafkaProducerManager:
    _instance = None
    _producer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_producer()
        return cls._instance
    
    def _initialize_producer(self):
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_request_size=10485760,  # 10MB for large frames
                compression_type='gzip',
                retries=3
            )
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def send(self, topic, value):
        if self._producer:
            return self._producer.send(topic, value=value)
        else:
            raise Exception("Kafka producer not initialized")
    
    def close(self):
        if self._producer:
            self._producer.close()

def get_kafka_producer():
    return KafkaProducerManager()

def get_kafka_consumer(topic, group_id=None, auto_offset_reset='latest'):
    try:
        return KafkaConsumer(
            topic,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
             )
    except Exception as e:
        logger.error(f"Failed to create Kafka consumer for topic {topic}: {e}")
        raise