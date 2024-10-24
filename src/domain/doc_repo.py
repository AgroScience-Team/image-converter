from abc import ABC, abstractmethod


class DocRepo(ABC):
    @abstractmethod
    def find_by_id(self, id: str):
        pass
