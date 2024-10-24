from abc import ABC, abstractmethod


class Mongo(ABC):
    @abstractmethod
    def find_by_id(self, id: str):
        pass
