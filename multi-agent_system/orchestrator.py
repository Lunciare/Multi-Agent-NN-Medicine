import openai
from pydantic import BaseModel
from agents.cardiologist import CardiologistAgent
from agents.dermatologist import DermatologistAgent
from agents.surgeon import SurgeonAgent
from config import client



class RouteDecision(BaseModel):
    specialist: str

class MedicalOrchestrator:
    def __init__(self):
        self.cardiologist = CardiologistAgent()
        self.dermatologist = DermatologistAgent()
        self.surgeon = SurgeonAgent()


    def route(self, question):
        response = client.responses.create(
              model="gpt-4o",
              input=f"""
              You are a medical orchestrator.

              Determine which specialist should handle the following request:
              - cardiologist
              - dermatologist
              - surgeon

              Respond strictly in one word.

              Patient request:
              {question}
              """
          )

        specialist = response.output_text.strip().lower()
        return specialist


    def answer(self, question):
        specialist = self.route(question)
        print("specialist: ", specialist)
        if specialist == "cardiologist":
            return self.cardiologist.answer(question)
        elif specialist == "dermatologist":
            return self.dermatologist.answer(question)
        elif specialist == "surgeon":
            return self.surgeon.answer(question)
        else:
            return "Could not determine the specialist."