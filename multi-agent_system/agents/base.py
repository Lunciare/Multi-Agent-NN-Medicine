from abc import ABC, abstractmethod

class BaseMedicalAgent(ABC):  
    @abstractmethod
    def answer(self, question):
        pass
