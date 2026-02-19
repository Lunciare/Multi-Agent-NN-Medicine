import os
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from agents.base import BaseMedicalAgent
from config import client



class CardiologistAgent(BaseMedicalAgent):

    def __init__(self, folder_path):
        self.embeddings = OpenAIEmbeddings()
        documents = []

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".txt"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                        if text:
                            documents.append(Document(page_content=text))

        self.vectorstore = FAISS.from_documents(documents, self.embeddings)

    def answer(self, question):
        docs = self.vectorstore.similarity_search(question, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])

        prompt = f"""
        You are a cardiologist. Answer the patient's question using the context below.
        If the answer is not in the context, reply that more information is needed.

        Context:
        {context}

        Patient question:
        {question}
        """

        response = client.responses.create(
            model="gpt-4o",
            input=prompt
          )
        
        return response.output_text.strip().lower()