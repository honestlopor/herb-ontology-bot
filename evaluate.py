"""
Herb Ontology Bot — Evaluation Script
======================================
Gold Standard Test Suite with 3-Layer Validation:
  Layer 1: SPARQL Syntax Validation    (Is the query parseable?)
  Layer 2: SPARQL Execution Validation (Does it run & return results?)
  Layer 3: Answer Correctness          (Precision / Recall / F1 vs gold answers)

Usage:
  export GEMINI_API_KEY="your-key"
  python evaluate.py
"""

import os
import re
import time
import google.generativeai as genai
from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

ONTOLOGY_FILE = "HerbMedicine_Ontology.ttl"
DELAY_BETWEEN_TESTS = 2  # seconds, to avoid rate-limiting

# ─────────────────────────────────────────────
# Load Ontology
# ─────────────────────────────────────────────
print("Loading ontology...")
g = Graph()
g.parse(ONTOLOGY_FILE, format="turtle")
print(f"✅ Ontology loaded ({len(g)} triples)\n")

# ─────────────────────────────────────────────
# Gold Standard Test Cases
# ─────────────────────────────────────────────
# Each test case has:
#   - scope:    which query scope it belongs to (1-6)
#   - question: the Thai question to ask the LLM
#   - expected: list of Thai strings that MUST appear in the results
#   - description: short English label for display

TEST_CASES = [
    # ── Scope 1: Medicine → Treats Conditions ──
    {
        "scope": 1,
        "description": "ยาหอมเทพจิตร treats what?",
        "question": "ยาหอมเทพจิตรรักษาอาการอะไรได้บ้าง?",
        "expected": [
            "วิงเวียน", "คลื่นไส้", "หน้ามืด", "ใจหวิว",
            "ใจสั่น", "ตาพร่า", "ตาลาย", "สวิงสวาย",
            "ลมกองละเอียด",
        ],
    },
    # ── Scope 1 Reverse: Condition → Medicines ──
    {
        "scope": 1,
        "description": "What medicines treat ท้องอืด?",
        "question": "ยาอะไรรักษาอาการท้องอืดได้บ้าง?",
        "expected": [
            "ยาเบญจกูล", "ยาขมิ้นชัน", "ยาธาตุบรรจบ",
            "ยาธาตุอบเชย", "ยาหอมนวโกฐ",
        ],
    },
    # ── Scope 2: Medicine → Formula Components ──
    {
        "scope": 2,
        "description": "ยาเบญจกูล ingredients?",
        "question": "ยาเบญจกูลมีส่วนประกอบอะไรบ้าง?",
        "expected": [
            "ดีปลี", "สะค้าน", "เจตมูลเพลิงแดง", "ขิง",
        ],
    },
    # ── Scope 3: Medicine → Dosage ──
    {
        "scope": 3,
        "description": "ยาขมิ้นชัน dosage?",
        "question": "ยาขมิ้นชันรับประทานขนาดเท่าไหร่?",
        "expected": [
            "500", "มิลลิกรัม", "1", "กรัม", "4", "ครั้ง",
        ],
    },
    # ── Scope 4: Medicine → Safety Alerts ──
    {
        "scope": 4,
        "description": "ยาหอมนวโกฐ safety alerts?",
        "question": "ยาหอมนวโกฐมีข้อห้ามใช้อะไรบ้าง?",
        "expected": [
            "ห้ามใช้ในหญิงตั้งครรภ์", "ผู้ที่มีไข้",
            "anticoagulants",
        ],
    },
    # ── Scope 4 Reverse: Condition → Safety Filter ──
    {
        "scope": 4,
        "description": "Medicines contraindicated for pregnant women?",
        "question": "ยาอะไรห้ามใช้ในหญิงตั้งครรภ์?",
        "expected": [
            "ยาหอมนวโกฐ", "ยาหอมอินทจักร์",
        ],
    },
    # ── Scope 5: Age Group → Medicines ──
    {
        "scope": 5,
        "description": "Medicines for children aged 6-12?",
        "question": "เด็กอายุ 6-12 ปี ใช้ยาอะไรได้บ้าง?",
        "expected": [
            "ยาธาตุบรรจบ",
        ],
    },
    # ── Scope 6: Group → Medicines ──
    {
        "scope": 6,
        "description": "Medicines in กลุ่มยาแก้ลมกองละเอียด?",
        "question": "กลุ่มยาแก้ลมกองละเอียดมียาอะไรบ้าง?",
        "expected": [
            "ยาหอมเทพจิตร", "ยาหอมแก้ลมวิงเวียน",
            "ยาหอมทิพโอสถ", "ยาหอมนวโกฐ", "ยาหอมอินทจักร์",
        ],
    },
]


# ─────────────────────────────────────────────
# Prompt Builder (same as main.py)
# ─────────────────────────────────────────────
def build_sparql_prompt(user_query: str) -> str:
    """Build the same prompt used in main.py."""
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
    5. For safety alerts: always fetch both ?alertMessage and ?alertSeverity
    6. For dosage: always fetch ?dosageInstruction, and use OPTIONAL for ?minDose ?maxDose
    7. For formula: chain ?medicine → hm:hasComponent → ?comp → hm:usesHerb → ?herb
    8. Always add LIMIT 20

    ════════════════════════════════════════
    FEW-SHOT EXAMPLES (6 scopes)
    ════════════════════════════════════════

    [Scope 1] Q: ยาหอมเทพจิตรรักษาอาการอะไรได้บ้าง?
    SELECT DISTINCT ?medicineNameThai ?conditionNameThai WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:treats ?condition .
    ?condition hm:nameThai ?conditionNameThai .
    FILTER(regex(?medicineNameThai, "เทพจิตร", "i"))
    }}}} LIMIT 20

    [Scope 1] Q: ยาอะไรรักษาอาการท้องอืดได้บ้าง?
    SELECT DISTINCT ?medicineNameThai WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:treats ?condition .
    FILTER(regex(str(?condition), "ท้องอืด", "i"))
    }}}} LIMIT 20

    [Scope 2] Q: ยาหอมเทพจิตรมีส่วนประกอบอะไรบ้าง?
    SELECT DISTINCT ?medicineNameThai ?herbNameThai ?plantPart ?quantity WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasComponent ?comp .
    ?comp hm:usesHerb ?herb .
    ?herb hm:nameThai ?herbNameThai .
    OPTIONAL {{{{ ?comp hm:usePlantPart ?part . ?part hm:nameThai ?plantPart }}}}
    OPTIONAL {{{{ ?comp hm:quantity ?quantity }}}}
    FILTER(regex(?medicineNameThai, "เทพจิตร", "i"))
    }}}} LIMIT 20

    [Scope 3] Q: ยาขมิ้นชันรับประทานขนาดเท่าไหร่?
    SELECT DISTINCT ?medicineNameThai ?dosageInstruction ?minDose ?maxDose ?form WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasGuideline ?guide .
    ?guide hm:dosageInstruction ?dosageInstruction .
    OPTIONAL {{{{ ?guide hm:minDose ?minDose }}}}
    OPTIONAL {{{{ ?guide hm:maxDose ?maxDose }}}}
    OPTIONAL {{{{ ?guide hm:forForm ?doseForm . ?doseForm hm:nameThai ?form }}}}
    FILTER(regex(?medicineNameThai, "ขมิ้นชัน", "i"))
    }}}} LIMIT 20

    [Scope 4] Q: ยาหอมนวโกฐมีข้อห้ามใช้อะไรบ้าง?
    SELECT DISTINCT ?medicineNameThai ?alertMessage ?alertSeverity WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasSafetyAlert ?alert .
    ?alert hm:alertMessage ?alertMessage .
    OPTIONAL {{{{ ?alert hm:alertSeverity ?alertSeverity }}}}
    FILTER(regex(?medicineNameThai, "นวโกฐ", "i"))
    }}}} LIMIT 20

    [Scope 4] Q: ยาอะไรห้ามใช้ในหญิงตั้งครรภ์?
    SELECT DISTINCT ?medicineNameThai ?alertMessage WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasSafetyAlert ?alert .
    ?alert hm:alertMessage ?alertMessage .
    ?alert hm:triggeredBy ?condition .
    FILTER(regex(str(?condition), "ตั้งครรภ์", "i"))
    }}}} LIMIT 20

    [Scope 5] Q: เด็กอายุ 6-12 ปี ใช้ยาอะไรได้บ้าง?
    SELECT DISTINCT ?medicineNameThai ?dosageInstruction WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:hasGuideline ?guide .
    ?guide hm:dosageInstruction ?dosageInstruction .
    ?guide hm:applicableTo ?ageCond .
    FILTER(regex(str(?ageCond), "6to12", "i"))
    }}}} LIMIT 20

    [Scope 6] Q: กลุ่มยาแก้ลมกองละเอียดมียาอะไรบ้าง?
    SELECT DISTINCT ?medicineNameThai ?groupName WHERE {{{{
    ?med rdf:type hm:HerbMedicine .
    ?med hm:nameThai ?medicineNameThai .
    ?med hm:belongsToGroup ?group .
    ?group hm:nameThai ?groupName .
    FILTER(regex(str(?group), "ลมกองละเอียด", "i"))
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
    """Layer 2: Execute SPARQL and return results as list of strings.
    Returns empty list on failure.
    """
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
    """Layer 3: Compute Precision, Recall, F1 using substring matching.

    A gold answer is considered 'found' if it appears as a substring
    in ANY result row. This is more robust than exact matching because
    the SPARQL results may contain surrounding text.
    """
    if not results and not expected:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    # Count how many expected items were found in results
    combined_results = "\n".join(results)
    found_expected = [e for e in expected if e in combined_results]

    # Recall: what fraction of expected items did we find?
    recall = len(found_expected) / len(expected) if expected else 0.0

    # For precision: we check how many result rows contain at least one expected item
    matched_rows = 0
    for row in results:
        if any(e in row for e in expected):
            matched_rows += 1
    precision = matched_rows / len(results) if results else 0.0

    # F1
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
# Main Evaluation Loop
# ─────────────────────────────────────────────
def run_evaluation():
    print("=" * 70)
    print("  HERB ONTOLOGY BOT — EVALUATION REPORT")
    print("=" * 70)
    print()

    all_results = []

    for i, tc in enumerate(TEST_CASES):
        test_num = i + 1
        print(f"── Test {test_num}/{len(TEST_CASES)}: [Scope {tc['scope']}] {tc['description']}")
        print(f"   Q: {tc['question']}")

        # Step 1: Generate SPARQL from LLM
        try:
            prompt = build_sparql_prompt(tc["question"])
            response = model.generate_content(prompt)
            sparql = clean_sparql_output(response.text)
        except Exception as e:
            print(f"   ❌ LLM error: {e}")
            all_results.append({
                "test": test_num,
                "scope": tc["scope"],
                "description": tc["description"],
                "syntax_valid": False,
                "has_results": False,
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
            })
            time.sleep(DELAY_BETWEEN_TESTS)
            continue

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
                for r in results[:5]:  # show first 5
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
        if metrics.get("missed"):
            print(f"   Missed: {metrics['missed']}")
        print()

        all_results.append({
            "test": test_num,
            "scope": tc["scope"],
            "description": tc["description"],
            "syntax_valid": syntax_ok,
            "has_results": has_results,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
        })

        # Rate limiting
        if i < len(TEST_CASES) - 1:
            time.sleep(DELAY_BETWEEN_TESTS)

    # ── Summary Table ──
    print()
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"{'#':<4} {'Scope':<6} {'Description':<45} {'Syn':>4} {'Res':>4} {'P':>5} {'R':>5} {'F1':>5}")
    print("-" * 70)

    for r in all_results:
        syn = "✅" if r["syntax_valid"] else "❌"
        res = "✅" if r["has_results"] else "❌"
        print(f"{r['test']:<4} {r['scope']:<6} {r['description']:<45} {syn:>4} {res:>4} {r['precision']:>5.2f} {r['recall']:>5.2f} {r['f1']:>5.2f}")

    # Overall averages
    n = len(all_results)
    avg_p = sum(r["precision"] for r in all_results) / n
    avg_r = sum(r["recall"] for r in all_results) / n
    avg_f1 = sum(r["f1"] for r in all_results) / n
    syntax_pass = sum(1 for r in all_results if r["syntax_valid"])
    exec_pass = sum(1 for r in all_results if r["has_results"])

    print("-" * 70)
    print(f"{'AVG':<4} {'':>6} {'':>45} {syntax_pass}/{n:>2} {exec_pass}/{n:>2} {avg_p:>5.2f} {avg_r:>5.2f} {avg_f1:>5.2f}")
    print()
    print(f"  Syntax Pass Rate : {syntax_pass}/{n} ({syntax_pass/n*100:.0f}%)")
    print(f"  Execution Pass   : {exec_pass}/{n} ({exec_pass/n*100:.0f}%)")
    print(f"  Avg Precision    : {avg_p:.2f}")
    print(f"  Avg Recall       : {avg_r:.2f}")
    print(f"  Avg F1 Score     : {avg_f1:.2f}")
    print()


if __name__ == "__main__":
    run_evaluation()
