import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import pytest
from kafka import KafkaProducer, KafkaConsumer
from minio import Minio
from pymongo import MongoClient
from testcontainers.core.container import DockerContainer
from testcontainers.kafka import KafkaContainer
from testcontainers.minio import MinioContainer
from testcontainers.mongodb import MongoDbContainer

from src.domain.models.multi_layer_tiff import MultiLayerTiff, Layer

# Константы
BUCKET_NAME = "agro-photos"
INPUT_TOPIC = "agro.s3.notifications"
OUTPUT_TOPIC = "agro.new.photos"
TEST_FILE_NAME = "test.tif"

EXPECTED_MESSAGE = {
    "photoId": "f128f7c6-1972-4a15-99b7-bca1e1675fdf",
    "contourId": "f128f7c6-1972-4a15-99b7-bca1e1675fdf",
    "date": "2024-08-02T12:00:00Z",
    "extension": "tif"
}

TEST_S3_NOTIFICATION = {
	"EventName": "s3:ObjectCreated:Put",
	"Key": "agro-photos/new/f128f7c6-1972-4a15-99b7-bca1e1675fdf.tiff"
}

data = MultiLayerTiff(
    extension="tif",
    date=datetime(2024, 8, 2, 12, 0, 0, tzinfo=timezone.utc),
    contourId="f128f7c6-1972-4a15-99b7-bca1e1675fdf",
    layers=[Layer(index="3", name="red"), Layer(index="5", name="nir")],
)

def get_url(container: DockerContainer, port: int) -> str:
    return f"{container.get_container_host_ip()}:{container.get_exposed_port(port)}"


@pytest.fixture(scope="module")
def minio_container():
    """Запускает MinIO контейнер и настраивает S3 клиент."""
    with MinioContainer() as minio:
        minio_client = Minio(
            get_url(minio, 9000),
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        minio_client.make_bucket(BUCKET_NAME)
        yield minio, minio_client


@pytest.fixture(scope="module")
def kafka_container():
    """Запускает Kafka контейнер."""
    with KafkaContainer().with_kraft() as kafka:
        yield kafka


@pytest.fixture(scope="module")
def mongo_container():
    """Запускает MongoDB контейнер."""
    with MongoDbContainer("mongo:latest", dbname="file_link_hub") as mongo:
        client = MongoClient(mongo.get_connection_url())

        db = client['file_link_hub']
        collection_out = db['photos']
        yield mongo, collection_out


def configure_env(minio, kafka, mongo):
    """Конфигурирует переменные окружения для приложения."""
    os.environ["kafka.bootstrap-servers"] = kafka.get_bootstrap_server()
    os.environ["KAFKA_SECURITY_PROTOCOL"] = "PLAINTEXT"
    os.environ["MONGO_CONNECTION_URL"] = mongo.get_connection_url()
    os.environ["MINIO_BUCKET"] = BUCKET_NAME
    os.environ["MINIO_URL"] = get_url(minio, 9000)
    os.environ["MINIO_ROOT_USER"] = "minioadmin"
    os.environ["MINIO_ROOT_PASSWORD"] = "minioadmin"
    os.environ["MINIO_CONSOLE_PORT"] = "9090"
    os.environ["MINIO_PORT"] = "9000"
    os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"


@pytest.fixture(scope="module")
def run_app(minio_container, kafka_container, mongo_container):
    """Запускает приложение с нужными переменными окружения."""

    # Получаем параметры окружения из контейнеров
    minio, _ = minio_container
    mongo, _ = mongo_container
    configure_env(minio, kafka_container, mongo)

    # Запуск процесса
    process = subprocess.Popen(
        ["python3", _absolute_path("../src/main.py")],
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=os.environ
    )

    yield process

    # Завершаем процесс после теста
    process.terminate()


def test_service_workflow(run_app, minio_container, kafka_container, mongo_container):
    """Основной тест обработки файлов через S3 и Kafka."""
    minio, minio_client = minio_container
    _, collection = mongo_container

    # Загрузка файла в MinIO
    file_path = "new/" + "f128f7c6-1972-4a15-99b7-bca1e1675fdf.tif"

    minio_client.fput_object(
        BUCKET_NAME, file_path, _absolute_path(TEST_FILE_NAME)
    )

    data_dict = data.model_dump()
    data_dict["_id"] = "f128f7c6-1972-4a15-99b7-bca1e1675fdf"
    data_dict["type"] = "MultiLayerTiff"

    # Сохранение в MongoDB
    collection.insert_one(data_dict)

    # Настройка Kafka producer & consumer
    producer = KafkaProducer(
        bootstrap_servers=kafka_container.get_bootstrap_server(),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    consumer = KafkaConsumer(
        OUTPUT_TOPIC,
        bootstrap_servers=kafka_container.get_bootstrap_server(),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )

    # Отправка сообщения в Kafka
    producer.send(INPUT_TOPIC, TEST_S3_NOTIFICATION)
    producer.flush()
    result = None
    timeout = time.time() + 20
    while time.time() < timeout:
        messages = consumer.poll(timeout_ms=1000)
        for _, records in messages.items():
            for record in records:
                result = record.value
                break
        if result:
            break

    assert result is not None, "Нет ответа от сервиса"
    assert result == EXPECTED_MESSAGE, f"Ожидаемое сообщение не совпадает. Получено: {result}"

    # Проверка, что в MinIO появился обработанный файл
    objects = minio_client.list_objects(bucket_name=BUCKET_NAME, recursive=True)
    files = [obj.object_name for obj in objects]

    expected_files = [
        f"converted/f128f7c6-1972-4a15-99b7-bca1e1675fdf-red.tif",
        f"converted/f128f7c6-1972-4a15-99b7-bca1e1675fdf-nir.tif"
    ]

    for expected_file in expected_files:
        assert expected_file in files, f"Файл {expected_file} не найден в MinIO"

def _absolute_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)