from abc import ABC, abstractmethod

from pydantic import BaseModel


class Worker(ABC):

    @abstractmethod
    def key(self) -> str:
        pass

    @abstractmethod
    def process(self, id: str, doc) -> BaseModel:
        pass
