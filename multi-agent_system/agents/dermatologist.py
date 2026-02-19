from agents.base import BaseMedicalAgent

class DermatologistAgent(BaseMedicalAgent):

    def answer(self, question):
        return "Агент-дерматолог недоступен"