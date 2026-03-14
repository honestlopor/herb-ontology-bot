import os
import re
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rdflib import Graph
# from dotenv import load_dotenve

# load_dotenv()

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
    You are a SPARQL expert for a Thai Herb Medicine Knowledge Graph (OWL2/RDF).
    Your ONLY job is to output a single valid SPARQL SELECT query. 
    No explanation. No markdown. No backticks. Just raw SPARQL.

    ════════════════════════════════════════
    PREFIXES (always include all of these)
    ════════════════════════════════════════
    PREFIX hm: <http://www.example.org/herbmedicine#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    ════════════════════════════════════════
    CLASS HIERARCHY (19 classes)
    ════════════════════════════════════════
    hm:HerbMedicine          ← ยาสมุนไพร (116 instances) — CORE CLASS
    hm:GroupMedicine         ← กลุ่มยา เช่น ยาแก้ลมกองละเอียด (25 instances)
    hm:Herb                  ← ตัวสมุนไพร เช่น ขมิ้นชัน กานพลู (441 instances)
    hm:FormulaComponent      ← ส่วนประกอบตำรับ (912 instances)
    hm:DosageGuideline       ← แนวทางการใช้ยา (244 instances)
    hm:DosageForm            ← รูปแบบยา เช่น ผง เม็ด แคปซูล (36 instances)
    hm:Frequency             ← ความถี่ เช่น วันละ 3 ครั้ง (5 instances)
    hm:Timing                ← เวลาทาน เช่น ก่อนอาหาร หลังอาหาร (7 instances)
    hm:UnitOfMeasurement     ← หน่วยวัด เช่น กรัม มิลลิกรัม (3 instances)
    hm:MedicalCondition
    └── hm:Disease         ← โรค (22 instances)
    └── hm:Symptom         ← อาการ (42 instances)
    hm:SafetyAlert
    └── hm:Contraindication ← ข้อห้ามใช้ (120 instances)
    └── hm:Caution          ← ข้อควรระวัง (366 instances)
    hm:PatientCondition
    └── hm:AgeCondition     ← เงื่อนไขอายุ (6 instances)
    └── hm:PhysiologicalState ← สภาวะสรีรวิทยา (3 instances)
    └── hm:AllergyCondition  ← ภาวะแพ้ (14 instances)
    hm:PlantPart             ← ส่วนของพืช เช่น เหง้า ใบ ดอก ราก (19 instances)

    ════════════════════════════════════════
    OBJECT PROPERTIES (15 properties)
    ════════════════════════════════════════
    hm:treats           HerbMedicine     → Disease / Symptom
    hm:hasSafetyAlert   HerbMedicine     → Contraindication / Caution
    hm:hasGuideline     HerbMedicine     → DosageGuideline
    hm:hasComponent     HerbMedicine     → FormulaComponent
    hm:belongsToGroup   HerbMedicine     → GroupMedicine
    hm:containsMedicine GroupMedicine    → HerbMedicine
    hm:usesHerb         FormulaComponent → Herb
    hm:usePlantPart     FormulaComponent → PlantPart
    hm:hasUnit          FormulaComponent → UnitOfMeasurement
    hm:forForm          DosageGuideline  → DosageForm
    hm:hasFrequency     DosageGuideline  → Frequency
    hm:hasTiming        DosageGuideline  → Timing
    hm:applicableTo     DosageGuideline  → AgeCondition
    hm:hasAgeCondition  SafetyAlert      → AgeCondition
    hm:triggeredBy      Contraindication/Caution → PatientCondition
                        (PatientCondition = AgeCondition | PhysiologicalState | AllergyCondition)

    ════════════════════════════════════════
    DATA PROPERTIES (14 properties)
    ════════════════════════════════════════
    hm:nameThai         → Thai name (xsd:string) — on HerbMedicine, Herb, Disease, Symptom, GroupMedicine
    hm:name             → English/Latin name (xsd:string)
    hm:alertMessage     → Warning text in Thai (xsd:string) — on Contraindication / Caution
    hm:alertSeverity    → "HIGH" | "MEDIUM" | "LOW" (xsd:string) — on SafetyAlert
    hm:dosageInstruction → Full instruction text in Thai (xsd:string) — on DosageGuideline
    hm:minDose          → Minimum dose (xsd:decimal)
    hm:maxDose          → Maximum dose (xsd:decimal)
    hm:quantity         → Ingredient amount (xsd:decimal) — on FormulaComponent
    hm:approvedBy       → Approval list reference (xsd:string) — on HerbMedicine

    ════════════════════════════════════════
    IRI NAMING PATTERNS (critical for FILTER)
    ════════════════════════════════════════
    Symptoms/Diseases    : hm:symptom_ท้องอืด, hm:symptom_วิงเวียน, hm:disease_ลมบาดทะจิต
    PhysiologicalState   : hm:physio_ตั้งครรภ์, hm:physio_มีไข้, hm:physio_ให้นมบุตร
    AgeCondition         : hm:agecond_child, hm:agecond_under6, hm:agecond_1to5,
                        hm:agecond_6to12, hm:agecond_1to3months, hm:agecond_4to6months
    GroupMedicine        : hm:group_ยาแก้ลมกองละเอียด, hm:group_ยาขับลมบรรเทาท้องอืดท้องเฟ้อ,
                        hm:group_ยาบำรุงธาตุปรับธาตุ

    → IRIs use Thai text directly — always use FILTER(regex(str(?var), "keyword", "i"))
    when matching Thai IRI values, NOT just ?var

    ════════════════════════════════════════
    QUERY RULES
    ════════════════════════════════════════
    1. Always SELECT ?medicineNameThai plus at least one meaningful result variable
    2. Use OPTIONAL {{ }} for properties that may not exist on every instance
    3. Use DISTINCT to avoid duplicate results
    4. Use FILTER(regex(str(?var), "keyword", "i")) for both IRI and literal matching
    5. When the user asks about ONE specific medicine by name, use EXACT match:
       FILTER(regex(?medicineNameThai, "^ยา<exact_name>$", "i"))
       Example: "ยาขมิ้นชัน" → FILTER(regex(?medicineNameThai, "^ยาขมิ้นชัน$", "i"))
       This prevents matching "ยาสารสกัดขมิ้นชัน" or "ยาทาขมิ้นชันและกัญชา"
       Only use substring match when the user wants ALL medicines containing a keyword.
    6. For safety alerts: always fetch both ?alertMessage and ?alertSeverity
    7. For dosage: always fetch ?dosageInstruction, and use OPTIONAL for ?minDose ?maxDose
    8. For formula: chain ?medicine → hm:hasComponent → ?comp → hm:usesHerb → ?herb
    9. Always add LIMIT 20

    ════════════════════════════════════════
    FEW-SHOT EXAMPLES (7 scopes)
    ════════════════════════════════════════

    [Scope 1] Q: ยาหอมเทพจิตรรักษาอาการอะไรได้บ้าง?
    SELECT DISTINCT ?medicineNameThai ?conditionNameThai WHERE {{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:treats ?condition .
    ?condition hm:nameThai ?conditionNameThai .
    FILTER(regex(?medicineNameThai, "เทพจิตร", "i"))
    }} LIMIT 20

    [Scope 1] Q: ยาอะไรรักษาอาการท้องอืดได้บ้าง?
    SELECT DISTINCT ?medicineNameThai WHERE {{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:treats ?condition .
    FILTER(regex(str(?condition), "ท้องอืด", "i"))
    }} LIMIT 20

    [Scope 2] Q: ยาหอมเทพจิตรมีส่วนประกอบอะไรบ้าง?
    SELECT DISTINCT ?medicineNameThai ?herbNameThai ?plantPart ?quantity WHERE {{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasComponent ?comp .
    ?comp hm:usesHerb ?herb .
    ?herb hm:nameThai ?herbNameThai .
    OPTIONAL {{ ?comp hm:usePlantPart ?part . ?part hm:nameThai ?plantPart }}
    OPTIONAL {{ ?comp hm:quantity ?quantity }}
    FILTER(regex(?medicineNameThai, "เทพจิตร", "i"))
    }} LIMIT 20

    [Scope 3] Q: ยาขมิ้นชันรับประทานขนาดเท่าไหร่?
    SELECT DISTINCT ?medicineNameThai ?dosageInstruction ?minDose ?maxDose ?form WHERE {{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasGuideline ?guide .
    ?guide hm:dosageInstruction ?dosageInstruction .
    OPTIONAL {{ ?guide hm:minDose ?minDose }}
    OPTIONAL {{ ?guide hm:maxDose ?maxDose }}
    OPTIONAL {{ ?guide hm:forForm ?doseForm . ?doseForm hm:nameThai ?form }}
    FILTER(regex(?medicineNameThai, "^ยาขมิ้นชัน$", "i"))
    }} LIMIT 20

    [Scope 4] Q: ยาหอมนวโกฐมีข้อห้ามใช้อะไรบ้าง?
    SELECT DISTINCT ?medicineNameThai ?alertMessage ?alertSeverity WHERE {{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasSafetyAlert ?alert .
    ?alert hm:alertMessage ?alertMessage .
    OPTIONAL {{ ?alert hm:alertSeverity ?alertSeverity }}
    FILTER(regex(?medicineNameThai, "นวโกฐ", "i"))
    }} LIMIT 20

    [Scope 4] Q: ยาอะไรห้ามใช้ในหญิงตั้งครรภ์?
    SELECT DISTINCT ?medicineNameThai ?alertMessage WHERE {{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasSafetyAlert ?alert .
    ?alert hm:alertMessage ?alertMessage .
    ?alert hm:triggeredBy ?condition .
    FILTER(regex(str(?condition), "ตั้งครรภ์", "i"))
    }} LIMIT 20

    [Scope 5] Q: ยาขมิ้นชันห้ามใช้ในบุคคลกลุ่มใดบ้าง?
    SELECT DISTINCT ?medicineNameThai ?alertMessage ?alertSeverity ?conditionLabel WHERE {{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasSafetyAlert ?alert .
    ?alert hm:alertMessage ?alertMessage .
    OPTIONAL {{ ?alert hm:alertSeverity ?alertSeverity }}
    ?alert hm:triggeredBy ?condition .
    OPTIONAL {{ ?condition hm:nameThai ?conditionLabel }}
    FILTER(regex(?medicineNameThai, "ขมิ้นชัน", "i"))
    }} LIMIT 20

    [Scope 6] Q: เด็กอายุ 6-12 ปี ใช้ยาอะไรได้บ้าง?
    SELECT DISTINCT ?medicineNameThai ?dosageInstruction WHERE {{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasGuideline ?guide .
    ?guide hm:dosageInstruction ?dosageInstruction .
    ?guide hm:applicableTo ?ageCond .
    FILTER(regex(str(?ageCond), "6to12", "i"))
    }} LIMIT 20

    [Scope 7] Q: กลุ่มยาแก้ลมกองละเอียดมียาอะไรบ้าง?
    SELECT DISTINCT ?medicineNameThai ?groupName WHERE {{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:belongsToGroup ?group .
    ?group hm:nameThai ?groupName .
    FILTER(regex(str(?group), "ลมกองละเอียด", "i"))
    }} LIMIT 20

    ════════════════════════════════════════
    USER QUESTION
    ════════════════════════════════════════
    "{user_query}"
    """
    
    try:
        ai_response = model.generate_content(prompt)
        print("AI Raw Response:\n", ai_response.text)
        executable_sparql = clean_sparql_output(ai_response.text)
        print("Generated SPARQL:\n", executable_sparql) 
        
        results = g.query(executable_sparql)
        
        answers = []
        for row in results:
            row_data = " | ".join([str(var) for var in row if var is not None])
            answers.append(row_data)
            
        if not answers:
            return {"reply": "ขออภัยครับ ไม่พบข้อมูลที่ตรงกับคำถามในฐานข้อมูลสมุนไพร"}
            
        answers = list(set(answers)) 
        raw_data_string = "\n".join(answers)
        print("Raw Database Results:\n", raw_data_string)
        
        generation_prompt = f"""
        คุณคือผู้ช่วยแพทย์แผนไทยที่เชี่ยวชาญและเป็นมิตร
        ผู้ใช้ถามคำถามว่า: "{user_query}"
        
        นี่คือข้อมูลดิบที่ค้นพบจากฐานข้อมูล Ontology ของเรา:
        {raw_data_string}
        
        หน้าที่ของคุณ:
        นำข้อมูลดิบด้านบนมาเรียบเรียงเป็นคำตอบภาษาไทยที่อ่านง่าย เป็นธรรมชาติ และตรงคำถาม
        
        กฎที่ต้องปฏิบัติตามอย่างเคร่งครัด:
        1. ห้ามแต่งเติมข้อมูลทางการแพทย์ อาการ หรือสรรพคุณที่ไม่มีระบุอยู่ในข้อมูลดิบเด็ดขาด
        2. หากข้อมูลมีหลายข้อ ให้จัดรูปแบบเป็น bullet points หรือย่อหน้าเพื่อให้อ่านง่าย
        3. ตอบกลับด้วยข้อความที่พร้อมแสดงผลให้ผู้ใช้เลย ไม่ต้องมีคำเกริ่นนำอธิบายการทำงานของคุณ
        """
        
        final_ai_response = model.generate_content(generation_prompt)
        print("Final Formatted Response:\n", final_ai_response.text)
        
        return {"reply": final_ai_response.text}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="ระบบไม่สามารถประมวลผลคำถามนี้ได้")