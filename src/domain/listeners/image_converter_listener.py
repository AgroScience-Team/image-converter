import json
from typing import Dict

from ioc.anotations.beans.component import Component
from ioc.anotations.proxy.log.log import Log
from ioc.anotations.proxy.scheduled.kafka_listener.kafka_listener import KafkaListener
from ioc.kafka.consumers.consumer_record import ConsumerRecord
from src.domain.doc_repo import DocRepo
from src.domain.listeners.abstract_listener import Listener
from src.domain.workers.worker import Worker
from src.infra.audit.audit import Audit


def _extract_file_name(file_key: str) -> str:
    parts = file_key.split('/')
    file_name_with_extension = parts[-1]
    file_name = file_name_with_extension.rsplit('.', 1)[0]
    return file_name


@Component()
class NdviWorkerListener(Listener):

    def __init__(self, workers: list[Worker], doc_repo: DocRepo) -> None:
        self.workers: Dict[str, Worker] = {worker.key(): worker for worker in workers}
        self.doc_repo = doc_repo

    @Audit("image-converter", "agro.audit.messages")
    @Log()
    @KafkaListener("image-converter", "agro.s3.notifications")
    def listen(self, message: ConsumerRecord):
        event_data = json.loads(message.value)

        event_name = event_data.get("EventName", "Unknown")
        file_key = _extract_file_name(event_data.get("Key", "Unknown"))

        print(f"Event Name: {event_name}, File Key: {file_key}")
        doc = self.doc_repo.find_by_id(file_key)
        type = doc.pop('type', "unknown")
        self.workers.get(type).process(file_key, doc)
