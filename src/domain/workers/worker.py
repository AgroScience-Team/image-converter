from abc import ABC, abstractmethod


class Worker(ABC):

    @abstractmethod
    def key(self) -> str:
        pass

    @abstractmethod
    def process(self, id: str, doc):
        pass
