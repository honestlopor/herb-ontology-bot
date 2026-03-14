"""
Herb Ontology Bot — Evaluation Script (10 Scopes)
===================================================
Gold Standard Test Suite with 3-Layer Validation:
  Layer 1: SPARQL Syntax Validation    (Is the query parseable?)
  Layer 2: SPARQL Execution Validation (Does it run & return results?)
  Layer 3: Answer Correctness          (Precision / Recall / F1 vs gold answers)

Covers all 10 query scopes:
  1.  Medicine → Group
  2.  Medicine → Herb Composition
  3.  Symptoms → Medicine
  4.  Medicine → Disease/Symptom (สรรพคุณ)
  5.  Contraindication
  6.  Caution (Drug Interactions)
  7.  Risk Groups (Group + Patient Condition filter)
  8.  Dosage Form
  9.  Usage Instructions
  10. Efficacy / Properties

Usage:
  export GEMINI_API_KEY="your-key"
  python evaluate.py
"""

import os
import re
import time
import json
import csv
from datetime import datetime
import google.generativeai as genai
from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

ONTOLOGY_FILE = "HerbMedicine_Ontology.ttl"
DELAY_BETWEEN_TESTS = 20  # seconds between API calls (free tier safe)
MAX_RETRIES = 5            # max retry attempts on rate-limit
INITIAL_BACKOFF = 10       # initial backoff in seconds
NUM_RUNS = 1               # number of evaluation runs (increase for mean ± std)

# ─────────────────────────────────────────────
# Load Ontology
# ─────────────────────────────────────────────
print("Loading ontology...")
g = Graph()
g.parse(ONTOLOGY_FILE, format="turtle")
print(f"✅ Ontology loaded ({len(g)} triples)\n")


def generate_with_retry(prompt: str) -> str:
    """Call Gemini with exponential backoff on rate-limit errors."""
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = any(kw in error_str for kw in [
                "429", "rate", "resource_exhausted", "quota",
                "too many requests", "resourceexhausted"
            ])
            if is_rate_limit and attempt < MAX_RETRIES - 1:
                wait = INITIAL_BACKOFF * (2 ** attempt)  # 10, 20, 40, 80...
                wait = min(wait, 60)  # cap at 60s
                print(f"    ⏳ Rate limited, retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                raise


# ─────────────────────────────────────────────
# Gold Standard Test Cases (10 Scopes)
# ─────────────────────────────────────────────
TEST_CASES = [
    # ── Scope 1: Medicine → Group ──
    {
        "scope": 1,
        "scope_name": "Medicine Group",
        "description": "ยาขมิ้นชัน belongs to which group?",
        "question": "ยาขมิ้นชันจัดอยู่ในกลุ่มใด",
        "expected": [
            "กลุ่มยาขับลมบรรเทาอาการท้องอืดท้องเฟ้อ",
        ],
    },
    # ── Scope 2: Medicine → Herb Composition ──
    {
        "scope": 2,
        "scope_name": "Herb Composition",
        "description": "ยาขมิ้นชัน herb ingredients?",
        "question": "ยาขมิ้นชันประกอบด้วยสมุนไพรชนิดใดบ้าง",
        "expected": [
            "ผงเหง้าขมิ้นชัน",
        ],
    },
    # ── Scope 3: Symptoms → Medicine ──
    {
        "scope": 3,
        "scope_name": "Symptoms",
        "description": "Symptoms หน้ามืด ตาลาย สวิงสวาย → medicine?",
        "question": "อาการ \"หน้ามืด ตาลาย สวิงสวาย\" ควรใช้ยาใด",
        "expected": [
            "ยาหอมเทพจิตร",
        ],
    },
    # ── Scope 4: Medicine → Disease/Conditions ──
    {
        "scope": 4,
        "scope_name": "Diseases",
        "description": "ยาหอมนวโกฐ treats what diseases?",
        "question": "ยาหอมนวโกฐใช้รักษาโรคใด",
        "expected": [
            "ลมจุกแน่นในอก", "ลมวิงเวียน", "ลมปลายไข้",
        ],
    },
    # ── Scope 5: Contraindication ──
    {
        "scope": 5,
        "scope_name": "Contraindication",
        "description": "ยาเบญจกูล contraindicated groups?",
        "question": "ยาเบญจกูล ห้ามใช้ในบุคคลกลุ่มใดบ้าง",
        "expected": [
            "ตั้งครรภ์", "มีไข้",
        ],
    },
    # ── Scope 6: Caution (Drug Interactions) ──
    {
        "scope": 6,
        "scope_name": "Caution",
        "description": "ยาขมิ้นชัน drug interaction cautions?",
        "question": "การใช้ยาขมิ้นชัน ควรระวังการใช้ร่วมกับยากลุ่มใด",
        "expected": [
            "anticoagulants", "antiplatelets", "CYP",
        ],
    },
    # ── Scope 7: Risk Groups (Group + Condition filter) ──
    {
        "scope": 7,
        "scope_name": "Risk Groups",
        "description": "Medicines in กลุ่มยาขับลม contraindicated for pregnant?",
        "question": "ยาใดบ้างในกลุ่มยาขับลมที่ระบุว่า \"ห้ามใช้ในหญิงตั้งครรภ์\"",
        "expected": [
            "ยาประสะกะเพรา", "ยาอภัยสาลี", "ยามันทธาตุ",
            "ยาเบญจกูล", "ยาวิสัมพยาใหญ่", "ยาประสะเจตพังคี",
            "ยาธาตุบรรจบ", "ยาประสะกานพลู",
        ],
    },
    # ── Scope 8: Dosage Form ──
    {
        "scope": 8,
        "scope_name": "Dosage Form",
        "description": "ยาหอมอินทจักร์ dosage forms?",
        "question": "ยาหอมอินทจักร์ มีรูปแบบยาใดบ้าง",
        "expected": [
            "ยาผง", "ยาเม็ด",
        ],
    },
    # ── Scope 9: Usage Instructions ──
    {
        "scope": 9,
        "scope_name": "Usage Instructions",
        "description": "ยาหอมเทพจิตร powder usage instructions?",
        "question": "วิธีรับประทานยาหอมเทพจิตรชนิดผง ต้องทำอย่างไร",
        "expected": [
            "1 - 1.4 กรัม", "ละลายน้ำ", "3 ครั้ง",
        ],
    },
    # ── Scope 10: Efficacy / Properties ──
    {
        "scope": 10,
        "scope_name": "Efficacy",
        "description": "ยาประสะจันทน์แดง efficacy?",
        "question": "สรรพคุณของยาประสะจันทน์แดง คืออะไร",
        "expected": [
            "ไข้พิษ", "ร้อนใน", "กระหายน้ำ",
        ],
    },
]


# ─────────────────────────────────────────────
# Prompt Builder (10-scope few-shot)
# ─────────────────────────────────────────────
def build_sparql_prompt(user_query: str) -> str:
    """Build the SPARQL generation prompt with 10-scope examples."""
    return f"""
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
    2. Use OPTIONAL {{{{ }}}} for properties that may not exist on every instance
    3. Use DISTINCT to avoid duplicate results
    4. Use FILTER(regex(str(?var), "keyword", "i")) for both IRI and literal matching
    5. When the user asks about ONE specific medicine by name, use EXACT match:
       FILTER(regex(?medicineNameThai, "^ยา<exact_name>$", "i"))
    6. For safety alerts: always fetch both ?alertMessage and ?alertSeverity
    7. For dosage: always fetch ?dosageInstruction, and use OPTIONAL for ?minDose ?maxDose
    8. For formula: chain ?medicine → hm:hasComponent → ?comp → hm:usesHerb → ?herb
    9. Always add LIMIT 20

    ════════════════════════════════════════
    FEW-SHOT EXAMPLES (10 scopes)
    ════════════════════════════════════════

    [Scope 1 — Medicine Group] Q: ยาขมิ้นชันจัดอยู่ในกลุ่มใด
    SELECT DISTINCT ?medicineNameThai ?groupName WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:belongsToGroup ?group .
    ?group hm:nameThai ?groupName .
    FILTER(regex(?medicineNameThai, "^ยาขมิ้นชัน$", "i"))
    }}}} LIMIT 20

    [Scope 2 — Herb Composition] Q: ยาขมิ้นชันประกอบด้วยสมุนไพรชนิดใดบ้าง
    SELECT DISTINCT ?medicineNameThai ?herbNameThai ?plantPart ?quantity WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasComponent ?comp .
    ?comp hm:usesHerb ?herb .
    ?herb hm:nameThai ?herbNameThai .
    OPTIONAL {{{{ ?comp hm:usePlantPart ?part . ?part hm:nameThai ?plantPart }}}}
    OPTIONAL {{{{ ?comp hm:quantity ?quantity }}}}
    FILTER(regex(?medicineNameThai, "^ยาขมิ้นชัน$", "i"))
    }}}} LIMIT 20

    [Scope 3 — Symptoms] Q: อาการ "หน้ามืด ตาลาย สวิงสวาย" ควรใช้ยาใด
    SELECT DISTINCT ?medicineNameThai ?conditionNameThai WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:treats ?condition .
    ?condition hm:nameThai ?conditionNameThai .
    FILTER(regex(str(?condition), "หน้ามืด|ตาลาย|สวิงสวาย", "i"))
    }}}} LIMIT 20

    [Scope 4 — Diseases] Q: ยาหอมนวโกฐใช้รักษาโรคใด
    SELECT DISTINCT ?medicineNameThai ?conditionNameThai WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:treats ?condition .
    ?condition hm:nameThai ?conditionNameThai .
    FILTER(regex(?medicineNameThai, "นวโกฐ", "i"))
    }}}} LIMIT 20

    [Scope 5 — Contraindication] Q: ยาเบญจกูล ห้ามใช้ในบุคคลกลุ่มใดบ้าง
    SELECT DISTINCT ?medicineNameThai ?alertMessage ?alertSeverity ?conditionLabel WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasSafetyAlert ?alert .
    ?alert rdf:type hm:Contraindication .
    ?alert hm:alertMessage ?alertMessage .
    OPTIONAL {{{{ ?alert hm:alertSeverity ?alertSeverity }}}}
    ?alert hm:triggeredBy ?condition .
    OPTIONAL {{{{ ?condition hm:nameThai ?conditionLabel }}}}
    FILTER(regex(?medicineNameThai, "^ยาเบญจกูล$", "i"))
    }}}} LIMIT 20

    [Scope 6 — Caution] Q: การใช้ยาขมิ้นชัน ควรระวังการใช้ร่วมกับยากลุ่มใด
    SELECT DISTINCT ?medicineNameThai ?alertMessage ?alertSeverity WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasSafetyAlert ?alert .
    ?alert rdf:type hm:Caution .
    ?alert hm:alertMessage ?alertMessage .
    OPTIONAL {{{{ ?alert hm:alertSeverity ?alertSeverity }}}}
    FILTER(regex(?medicineNameThai, "^ยาขมิ้นชัน$", "i"))
    }}}} LIMIT 20

    [Scope 7 — Risk Groups] Q: ยาใดบ้างในกลุ่มยาขับลมที่ระบุว่า "ห้ามใช้ในหญิงตั้งครรภ์"
    SELECT DISTINCT ?medicineNameThai ?groupName ?alertMessage WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:belongsToGroup ?group .
    ?group hm:nameThai ?groupName .
    ?med hm:hasSafetyAlert ?alert .
    ?alert hm:alertMessage ?alertMessage .
    ?alert hm:triggeredBy ?condition .
    FILTER(regex(str(?group), "ขับลม", "i"))
    FILTER(regex(str(?condition), "ตั้งครรภ์", "i"))
    }}}} LIMIT 20

    [Scope 8 — Dosage Form] Q: ยาหอมอินทจักร์ มีรูปแบบยาใดบ้าง
    SELECT DISTINCT ?medicineNameThai ?formName WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasGuideline ?guide .
    ?guide hm:forForm ?form .
    ?form hm:nameThai ?formName .
    FILTER(regex(?medicineNameThai, "อินทจักร์", "i"))
    }}}} LIMIT 20

    [Scope 9 — Usage Instructions] Q: วิธีรับประทานยาหอมเทพจิตรชนิดผง ต้องทำอย่างไร
    SELECT DISTINCT ?medicineNameThai ?dosageInstruction ?formName WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasGuideline ?guide .
    ?guide hm:dosageInstruction ?dosageInstruction .
    ?guide hm:forForm ?form .
    ?form hm:nameThai ?formName .
    FILTER(regex(?medicineNameThai, "เทพจิตร", "i"))
    FILTER(regex(?formName, "ผง", "i"))
    }}}} LIMIT 20

    [Scope 10 — Efficacy] Q: สรรพคุณของยาประสะจันทน์แดง คืออะไร
    SELECT DISTINCT ?medicineNameThai ?conditionNameThai WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:treats ?condition .
    ?condition hm:nameThai ?conditionNameThai .
    FILTER(regex(?medicineNameThai, "ประสะจันทน์แดง", "i"))
    }}}} LIMIT 20

    ════════════════════════════════════════
    USER QUESTION
    ════════════════════════════════════════
    "{user_query}"
    """


def clean_sparql_output(raw_text: str) -> str:
    """Remove markdown code fences from LLM output."""
    cleaned = re.sub(r"```(sparql)?(.*?)```", r"\2", raw_text, flags=re.DOTALL)
    return cleaned.strip()


# ─────────────────────────────────────────────
# Evaluation Functions
# ─────────────────────────────────────────────
def validate_sparql_syntax(sparql: str) -> bool:
    """Layer 1: Check if SPARQL query is syntactically valid."""
    try:
        prepareQuery(sparql)
        return True
    except Exception:
        return False


def execute_sparql(sparql: str) -> list[str]:
    """Layer 2: Execute SPARQL and return results as list of strings."""
    try:
        results = g.query(sparql)
        rows = []
        for row in results:
            row_str = " | ".join([str(var) for var in row if var is not None])
            rows.append(row_str)
        return list(set(rows))  # deduplicate
    except Exception as e:
        print(f"    ⚠️ Execution error: {e}")
        return []


def compute_metrics(results: list[str], expected: list[str]) -> dict:
    """Layer 3: Compute Precision, Recall, F1 using substring matching."""
    if not results and not expected:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    combined_results = "\n".join(results)
    found_expected = [e for e in expected if e in combined_results]

    recall = len(found_expected) / len(expected) if expected else 0.0

    matched_rows = 0
    for row in results:
        if any(e in row for e in expected):
            matched_rows += 1
    precision = matched_rows / len(results) if results else 0.0

    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "found": found_expected,
        "missed": [e for e in expected if e not in found_expected],
    }


# ─────────────────────────────────────────────
# Single Evaluation Run
# ─────────────────────────────────────────────
def run_single_evaluation(run_num: int) -> list[dict]:
    """Run one complete evaluation pass. Returns list of result dicts."""
    print(f"\n{'━' * 70}")
    print(f"  RUN {run_num}")
    print(f"{'━' * 70}\n")

    all_results = []

    for i, tc in enumerate(TEST_CASES):
        test_num = i + 1
        print(f"── Test {test_num}/{len(TEST_CASES)}: [Scope {tc['scope']} — {tc['scope_name']}] {tc['description']}")
        print(f"   Q: {tc['question']}")

        start_time = time.time()

        # Step 1: Generate SPARQL from LLM
        try:
            prompt = build_sparql_prompt(tc["question"])
            raw_text = generate_with_retry(prompt)
            sparql = clean_sparql_output(raw_text)
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ LLM error: {e}")
            all_results.append({
                "test": test_num,
                "scope": tc["scope"],
                "scope_name": tc["scope_name"],
                "description": tc["description"],
                "syntax_valid": False,
                "has_results": False,
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "latency": elapsed,
            })
            time.sleep(DELAY_BETWEEN_TESTS)
            continue

        elapsed = time.time() - start_time

        print(f"   Generated SPARQL:")
        for line in sparql.split("\n"):
            print(f"     {line}")

        # Layer 1: Syntax Validation
        syntax_ok = validate_sparql_syntax(sparql)
        print(f"   Layer 1 — Syntax:    {'✅ Valid' if syntax_ok else '❌ Invalid'}")

        # Layer 2: Execution
        if syntax_ok:
            results = execute_sparql(sparql)
            has_results = len(results) > 0
            print(f"   Layer 2 — Execution: {'✅' if has_results else '⚠️'} {len(results)} result(s)")
            if results:
                for r in results[:5]:
                    print(f"     → {r}")
                if len(results) > 5:
                    print(f"     ... and {len(results) - 5} more")
        else:
            results = []
            has_results = False
            print(f"   Layer 2 — Execution: ⏭️ Skipped (syntax invalid)")

        # Layer 3: Answer Correctness
        metrics = compute_metrics(results, tc["expected"])
        print(f"   Layer 3 — Precision: {metrics['precision']:.2f}  Recall: {metrics['recall']:.2f}  F1: {metrics['f1']:.2f}")
        print(f"   ⏱️ Latency: {elapsed:.1f}s")
        if metrics.get("missed"):
            print(f"   Missed: {metrics['missed']}")
        print()

        all_results.append({
            "test": test_num,
            "scope": tc["scope"],
            "scope_name": tc["scope_name"],
            "description": tc["description"],
            "syntax_valid": syntax_ok,
            "has_results": has_results,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "latency": elapsed,
        })

        # Rate limiting
        if i < len(TEST_CASES) - 1:
            time.sleep(DELAY_BETWEEN_TESTS)

    return all_results


# ─────────────────────────────────────────────
# Multi-Run Evaluation with Statistics
# ─────────────────────────────────────────────
def run_evaluation():
    print("=" * 70)
    print("  HERB ONTOLOGY BOT — EVALUATION REPORT")
    print(f"  Model: gemini-2.5-flash  |  Runs: {NUM_RUNS}  |  Tests: {len(TEST_CASES)}")
    print("=" * 70)

    all_runs = []
    for run_num in range(1, NUM_RUNS + 1):
        run_results = run_single_evaluation(run_num)
        all_runs.append(run_results)

        if run_num < NUM_RUNS:
            wait = 30
            print(f"⏳ Waiting {wait}s before next run...\n")
            time.sleep(wait)

    # ── Per-Scope Summary (mean ± std across runs) ──
    import statistics

    print()
    print("=" * 70)
    print("  SUMMARY (mean ± std across runs)")
    print("=" * 70)

    header = f"{'Scope':<8} {'Name':<22} {'Syntax%':>8} {'Exec%':>8} {'P':>10} {'R':>10} {'F1':>10} {'Lat(s)':>10}"
    print(header)
    print("-" * 86)

    scope_stats = {}
    for scope_num in range(1, 11):
        scope_precision = []
        scope_recall = []
        scope_f1 = []
        scope_latency = []
        scope_syntax = []
        scope_exec = []
        scope_name = ""

        for run_results in all_runs:
            for r in run_results:
                if r["scope"] == scope_num:
                    scope_precision.append(r["precision"])
                    scope_recall.append(r["recall"])
                    scope_f1.append(r["f1"])
                    scope_latency.append(r["latency"])
                    scope_syntax.append(1.0 if r["syntax_valid"] else 0.0)
                    scope_exec.append(1.0 if r["has_results"] else 0.0)
                    scope_name = r["scope_name"]

        if not scope_precision:
            continue

        def fmt_stat(values):
            if len(values) == 1:
                return f"{values[0]:.2f}"
            mean = statistics.mean(values)
            std = statistics.stdev(values) if len(values) > 1 else 0.0
            return f"{mean:.2f}±{std:.2f}"

        syn_rate = f"{statistics.mean(scope_syntax)*100:.0f}%"
        exec_rate = f"{statistics.mean(scope_exec)*100:.0f}%"

        print(f"{scope_num:<8} {scope_name:<22} {syn_rate:>8} {exec_rate:>8} {fmt_stat(scope_precision):>10} {fmt_stat(scope_recall):>10} {fmt_stat(scope_f1):>10} {fmt_stat(scope_latency):>10}")

        scope_stats[scope_num] = {
            "scope_name": scope_name,
            "precision": scope_precision,
            "recall": scope_recall,
            "f1": scope_f1,
            "latency": scope_latency,
            "syntax": scope_syntax,
            "exec": scope_exec,
        }

    # ── Overall Summary ──
    all_p = [r["precision"] for run in all_runs for r in run]
    all_r = [r["recall"] for run in all_runs for r in run]
    all_f1 = [r["f1"] for run in all_runs for r in run]
    all_lat = [r["latency"] for run in all_runs for r in run]
    all_syn = [1.0 if r["syntax_valid"] else 0.0 for run in all_runs for r in run]
    all_exec = [1.0 if r["has_results"] else 0.0 for run in all_runs for r in run]

    print("-" * 86)
    avg_p = statistics.mean(all_p)
    avg_r = statistics.mean(all_r)
    avg_f1_val = statistics.mean(all_f1)
    std_p = statistics.stdev(all_p) if len(all_p) > 1 else 0.0
    std_r = statistics.stdev(all_r) if len(all_r) > 1 else 0.0
    std_f1 = statistics.stdev(all_f1) if len(all_f1) > 1 else 0.0
    avg_lat = statistics.mean(all_lat)
    std_lat = statistics.stdev(all_lat) if len(all_lat) > 1 else 0.0

    print(f"{'OVERALL':<30} {statistics.mean(all_syn)*100:>8.0f}% {statistics.mean(all_exec)*100:>8.0f}% {avg_p:>5.2f}±{std_p:.2f} {avg_r:>5.2f}±{std_r:.2f} {avg_f1_val:>5.2f}±{std_f1:.2f} {avg_lat:>5.1f}±{std_lat:.1f}")

    print()
    print(f"  Syntax Pass Rate     : {statistics.mean(all_syn)*100:.0f}%")
    print(f"  Execution Pass Rate  : {statistics.mean(all_exec)*100:.0f}%")
    print(f"  Avg Precision        : {avg_p:.2f} ± {std_p:.2f}")
    print(f"  Avg Recall           : {avg_r:.2f} ± {std_r:.2f}")
    print(f"  Avg F1 Score         : {avg_f1_val:.2f} ± {std_f1:.2f}")
    print(f"  Avg Latency          : {avg_lat:.1f}s ± {std_lat:.1f}s")
    print(f"  Total API Calls      : {len(TEST_CASES) * NUM_RUNS}")
    print()

    # ── Save Results to JSON and CSV ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON output
    output = {
        "metadata": {
            "model": "gemini-2.5-flash",
            "num_runs": NUM_RUNS,
            "num_tests": len(TEST_CASES),
            "timestamp": timestamp,
            "delay_between_tests": DELAY_BETWEEN_TESTS,
        },
        "overall": {
            "precision": {"mean": round(avg_p, 4), "std": round(std_p, 4)},
            "recall": {"mean": round(avg_r, 4), "std": round(std_r, 4)},
            "f1": {"mean": round(avg_f1_val, 4), "std": round(std_f1, 4)},
            "syntax_pass_rate": round(statistics.mean(all_syn), 4),
            "execution_pass_rate": round(statistics.mean(all_exec), 4),
            "avg_latency": round(avg_lat, 2),
        },
        "per_scope": {},
        "raw_runs": [],
    }

    for scope_num, stats in scope_stats.items():
        output["per_scope"][f"scope_{scope_num}"] = {
            "name": stats["scope_name"],
            "precision": {"mean": round(statistics.mean(stats["precision"]), 4), "std": round(statistics.stdev(stats["precision"]) if len(stats["precision"]) > 1 else 0.0, 4)},
            "recall": {"mean": round(statistics.mean(stats["recall"]), 4), "std": round(statistics.stdev(stats["recall"]) if len(stats["recall"]) > 1 else 0.0, 4)},
            "f1": {"mean": round(statistics.mean(stats["f1"]), 4), "std": round(statistics.stdev(stats["f1"]) if len(stats["f1"]) > 1 else 0.0, 4)},
        }

    for run_idx, run_results in enumerate(all_runs):
        output["raw_runs"].append([{
            "test": r["test"],
            "scope": r["scope"],
            "scope_name": r["scope_name"],
            "description": r["description"],
            "syntax_valid": r["syntax_valid"],
            "has_results": r["has_results"],
            "precision": round(r["precision"], 4),
            "recall": round(r["recall"], 4),
            "f1": round(r["f1"], 4),
            "latency": round(r["latency"], 2),
        } for r in run_results])

    json_path = f"eval_results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"📄 Results saved to: {json_path}")

    # CSV output (flat per-test per-run)
    csv_path = f"eval_results_{timestamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Run", "Test", "Scope", "Scope_Name", "Description",
                         "Syntax_Valid", "Has_Results", "Precision", "Recall", "F1", "Latency_s"])
        for run_idx, run_results in enumerate(all_runs):
            for r in run_results:
                writer.writerow([
                    run_idx + 1, r["test"], r["scope"], r["scope_name"],
                    r["description"], r["syntax_valid"], r["has_results"],
                    round(r["precision"], 4), round(r["recall"], 4),
                    round(r["f1"], 4), round(r["latency"], 2),
                ])
    print(f"📊 CSV saved to: {csv_path}")
    print()


if __name__ == "__main__":
    run_evaluation()
