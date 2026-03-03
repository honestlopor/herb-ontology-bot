import os
import re
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rdflib import Graph

app = FastAPI(title="Herb Medicine Ontology Chatbot")

# Gemini API Key
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# Load the Ontology Model
g = Graph()
try:
    g.parse("HerbMedicine_Ontology.ttl", format="turtle") 
    print("Herb Medicine Ontology loaded successfully!")
except Exception as e:
    print(f"Error loading ontology: {e}")

class ChatRequest(BaseModel):
    user_id: str
    question: str

def clean_sparql_output(raw_text: str) -> str:
    cleaned = re.sub(r"```(sparql)?(.*?)```", r"\2", raw_text, flags=re.DOTALL)
    return cleaned.strip()

@app.post("/api/chat")
async def chat_with_ontology(request: ChatRequest):
    user_query = request.question
    
    prompt = f"""
    You are an expert in Semantic Web and SPARQL. 
    Convert the user's question into a valid SPARQL Query to search a Herb Medicine Knowledge Graph.
    
    Ontology Schema Information:
    - Base Prefix: PREFIX hm: <http://www.example.org/herbmedicine#>
    - Standard Prefixes: PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    Key Classes:
    - hm:HerbMedicine (e.g., Andrographis Capsule)
    - hm:Disease / hm:Symptom (e.g., Common Cold, Fever)
    - hm:SafetyAlert / hm:Contraindication / hm:Caution
    - hm:DosageGuideline
    
    Key Object Properties (Relationships):
    - ?medicine hm:treats ?diseaseOrSymptom
    - ?medicine hm:hasSafetyAlert ?alert
    - ?medicine hm:hasGuideline ?guideline
    
    Key Data Properties (Attributes):
    - hm:name (English name)
    - hm:nameThai (Thai name)
    - hm:alertMessage (Warning text)
    - hm:dosageInstruction (How to use)

    User's question: "{user_query}"
    
    Instructions for generating SPARQL:
    1. Reply ONLY with the SPARQL query. No other explanations.
    2. The query must be executable.
    3. Use 'FILTER(regex(?variable, "Keyword", "i"))' if the user searches by name, as they might type in Thai or English.
    4. Select meaningful variables to return, like ?medicineNameThai, ?instruction, or ?alertMessage.
    """
    
    try:
        ai_response = model.generate_content(prompt)
        print("AI Raw Response:\n", ai_response.text)
        executable_sparql = clean_sparql_output(ai_response.text)
        print("Generated SPARQL:\n", executable_sparql) 

        # Query the Graph
        results = g.query(executable_sparql)
        
        # Format the response
        answers = []
        for row in results:
            # Join multiple variables returned by SELECT into a single string line
            row_data = " | ".join([str(var) for var in row if var is not None])
            answers.append(row_data)
            
        if not answers:
            return {"reply": "Sorry, I couldn't find an exact answer in the herb medicine database."}
            
        for answer in answers:
            print("SPARQL Result:", answer)
        
        answers = list(set(answers)) 
        formatted_reply = "Here is what I found:\n- " + "\n- ".join(answers)
        
        return {"reply": formatted_reply}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="The system could not process this question.")