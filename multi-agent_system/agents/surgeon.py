from agents.base import BaseMedicalAgent

class SurgeonAgent(BaseMedicalAgent):

    def answer(self, question):
        return "Агент-хирург недоступен"