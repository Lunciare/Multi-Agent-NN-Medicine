from orchestrator import MedicalOrchestrator

if __name__ == "__main__":
    orchestrator = MedicalOrchestrator("data/cardiology")

    question = input("Enter the patient's question: ")
    answer = orchestrator.answer(question)

    print("\nAnswer:")
    print(answer)
