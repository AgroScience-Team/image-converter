from ioc.anotations.beans.component import Component
from ioc.mongo.mongo import Mongo
from src.domain.doc_repo import DocRepo


@Component()
class DocRepoImpl(DocRepo):

    def find_by_id(self, id: str):
        return self.mongo.find_by_id(id)

    def __init__(self, mongo: Mongo) -> None:
        self.mongo = mongo
