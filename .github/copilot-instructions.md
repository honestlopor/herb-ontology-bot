# Thai Herb Medicine Ontology Chatbot - AI Agent Instructions

## Architecture Overview
This is a dual-component Thai herb medicine chatbot:
- **Backend** (`main.py`): FastAPI service using Google Gemini AI to generate SPARQL queries against an OWL ontology
- **Frontend** (`app.py`): Streamlit chat interface that calls the backend API
- **Data** (`HerbMedicine_Ontology.ttl`): 12K+ line OWL ontology with Thai herb medicine knowledge (116 medicines, 441 herbs, safety alerts, dosages)

## Core Workflow
1. User asks question in Thai via Streamlit UI
2. Streamlit sends request to FastAPI `/api/chat` endpoint
3. Gemini AI generates SPARQL query using detailed ontology schema and few-shot examples
4. Query executes against RDFLib-loaded ontology
5. Results formatted and returned to user

## Critical Patterns

### SPARQL Query Generation
Always use Gemini with this exact prompt structure from `main.py` lines 25-200:
- Include ALL prefixes (hm:, rdf:, rdfs:, xsd:)
- Use `FILTER(regex(str(?var), "keyword", "i"))` for Thai IRI matching (not just `?var`)
- Always `SELECT DISTINCT` with `LIMIT 20`
- Use `OPTIONAL {{ }}` blocks for properties that may not exist
- IRI patterns: `hm:symptom_ท้องอืด`, `hm:disease_ลมบาดทะจิต`, `hm:physio_ตั้งครรภ์`

### Thai Language Handling
- All user queries and responses in Thai
- Ontology contains both Thai (`hm:nameThai`) and English (`hm:name`) names
- Regex matching is case-insensitive (`"i"` flag) for Thai text
- Safety alerts and dosage instructions stored as Thai strings

### Key Entity Relationships
```sparql
# Medicine treats conditions
?med hm:treats ?condition

# Medicine has components using herbs
?med hm:hasComponent ?comp . ?comp hm:usesHerb ?herb

# Medicine has safety alerts
?med hm:hasSafetyAlert ?alert . ?alert hm:alertMessage ?msg

# Medicine belongs to groups
?med hm:belongsToGroup ?group
```

## Development Setup
```bash
# Activate virtual environment
source herb-venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export GEMINI_API_KEY="your-key-here"

# Run backend
uvicorn main:app --reload

# Run frontend (separate terminal)
streamlit run app.py
```

## Common Query Scopes
1. **Treatment queries**: "ยาอะไรรักษาอาการX" (what medicine treats symptom X)
2. **Composition queries**: "ยาXมีส่วนประกอบอะไร" (what are ingredients of medicine X)
3. **Dosage queries**: "ยาXรับประทานขนาดเท่าไหร่" (what dosage for medicine X)
4. **Safety queries**: "ยาXมีข้อห้ามใช้อะไร" (what contraindications for medicine X)
5. **Age-specific queries**: "เด็กอายุXใช้ยาอะไรได้" (what medicines for children age X)
6. **Group queries**: "กลุ่มยาXมียาอะไรบ้าง" (what medicines in group X)

## Ontology Schema Reference
- **Core class**: `hm:HerbMedicine` (116 instances)
- **Key properties**: `hm:nameThai`, `hm:treats`, `hm:hasComponent`, `hm:hasSafetyAlert`
- **Safety**: Always fetch both `?alertMessage` and `?alertSeverity`
- **Dosage**: Always include `?dosageInstruction`, optionally `?minDose`/`?maxDose`

## Error Handling
- Ontology loading failures logged but don't crash app
- Gemini API failures return HTTP 500
- Empty SPARQL results return "couldn't find exact answer" message
- All exceptions caught and logged with `print()` statements

## File Structure
- `main.py`: FastAPI backend with Gemini integration
- `app.py`: Streamlit frontend with custom CSS styling
- `HerbMedicine_Ontology.ttl`: OWL ontology data
- `requirements.txt`: Python dependencies
- `herb-venv/`: Pre-configured virtual environment</content>
<parameter name="filePath">/Users/lopor/Documents/cs/ontology/thai-herbs/herb-ontology-bot/.github/copilot-instructions.md