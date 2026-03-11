# SWRL Rules for HerbMedicine_Ontology

เอกสารนี้รวบรวม SWRL (Semantic Web Rule Language) Rules ระดับ Expert สำหรับ `HerbMedicine_Ontology.ttl`
สามารถนำไปใส่ใน **Protégé** ได้โดยตรง ผ่านแท็บ **SWRLTab** หรือ **Rules**

> **หมายเหตุ:** ในการรัน SWRL Rules ใน Protégé ต้องเปิดใช้งาน Reasoner เช่น **Pellet** หรือ **HermiT** ก่อน

---

## Prefix ที่ใช้

```
hm: = http://www.example.org/herbmedicine#
swrlb: = http://www.w3.org/2003/11/swrlb#
```

---

## 1. Transitive Treatment Inference (การอนุมานยาที่รักษาอาการผ่านกลุ่มยา)

**แนวคิด:** ถ้ายา (?m) อยู่ในกลุ่มยา (?g) และ กลุ่มยานั้นอยู่ภายใต้ระบบ (?sys) แสดงว่ายานั้นเป็นส่วนหนึ่งของระบบการรักษานั้น

**ประโยชน์:** สร้าง Property ใหม่ `belongsToSystem` เพื่อให้ Query ได้ว่ายาตำรับนี้อยู่ภายใต้ระบบรักษาอะไร โดยไม่ต้อง Query ซ้อนหลายชั้น

```
SWRL Rule:
HerbMedicine(?m) ∧ belongsToGroup(?m, ?g) ∧ containsMedicine(?sys, ?g) ∧ GroupMedicine(?sys)
→ belongsToSystem(?m, ?sys)
```

**Protégé Syntax:**
```
HerbMedicine(?m), belongsToGroup(?m, ?g), containsMedicine(?sys, ?g), GroupMedicine(?sys)
-> belongsToSystem(?m, ?sys)
```

---

## 2. Pregnancy Safety Flag (ระบบแจ้งเตือนยาอันตรายสำหรับหญิงตั้งครรภ์)

**แนวคิด:** ถ้ายา (?m) มี SafetyAlert ที่เป็น Contraindication และถูก triggeredBy สภาวะ "ตั้งครรภ์" แสดงว่ายานั้นต้องถูก Flag ว่า `isUnsafeForPregnancy = true`

**ประโยชน์:** สร้าง Data Property `isUnsafeForPregnancy` เป็น Boolean เพื่อให้ Application ดึงข้อมูลไปแจ้งเตือนได้ทันที

```
SWRL Rule:
HerbMedicine(?m) ∧ hasSafetyAlert(?m, ?a) ∧ Contraindication(?a) ∧ triggeredBy(?a, hm:physio_ตั้งครรภ์)
→ isUnsafeForPregnancy(?m, true)
```

**Protégé Syntax:**
```
HerbMedicine(?m), hasSafetyAlert(?m, ?a), Contraindication(?a), triggeredBy(?a, hm:physio_ตั้งครรภ์)
-> isUnsafeForPregnancy(?m, true)
```

---

## 3. Lactation Safety Flag (ระบบแจ้งเตือนยาอันตรายสำหรับหญิงให้นมบุตร)

**แนวคิด:** เช่นเดียวกับ Rule 2 แต่สำหรับสภาวะ "ให้นมบุตร"

```
SWRL Rule:
HerbMedicine(?m) ∧ hasSafetyAlert(?m, ?a) ∧ Contraindication(?a) ∧ triggeredBy(?a, hm:physio_ให้นมบุตร)
→ isUnsafeForLactation(?m, true)
```

**Protégé Syntax:**
```
HerbMedicine(?m), hasSafetyAlert(?m, ?a), Contraindication(?a), triggeredBy(?a, hm:physio_ให้นมบุตร)
-> isUnsafeForLactation(?m, true)
```

---

## 4. Fever Contraindication Flag (ห้ามใช้ขณะมีไข้)

**แนวคิด:** ยาบางตำรับห้ามใช้เมื่อผู้ป่วยมีไข้ ระบบจะ Flag อัตโนมัติ

```
SWRL Rule:
HerbMedicine(?m) ∧ hasSafetyAlert(?m, ?a) ∧ Contraindication(?a) ∧ triggeredBy(?a, hm:physio_มีไข้)
→ isUnsafeDuringFever(?m, true)
```

**Protégé Syntax:**
```
HerbMedicine(?m), hasSafetyAlert(?m, ?a), Contraindication(?a), triggeredBy(?a, hm:physio_มีไข้)
-> isUnsafeDuringFever(?m, true)
```

---

## 5. Herb-to-Symptom Inference (การอนุมานสมุนไพรกับอาการที่รักษาได้)

**แนวคิด:** ถ้าสมุนไพร (?h) เป็นส่วนประกอบของยา (?m) และยานั้นรักษาอาการ (?s) ได้ แสดงว่าสมุนไพรนั้น "มีส่วนช่วยรักษา" อาการนั้น

**ประโยชน์:** สร้าง Property ใหม่ `herbContributesToTreating` เชื่อม Herb กับ MedicalCondition ได้โดยตรงโดยไม่ต้องผ่าน Medicine ก่อน

```
SWRL Rule:
HerbMedicine(?m) ∧ hasComponent(?m, ?c) ∧ usesHerb(?c, ?h) ∧ treats(?m, ?s)
→ herbContributesToTreating(?h, ?s)
```

**Protégé Syntax:**
```
HerbMedicine(?m), hasComponent(?m, ?c), usesHerb(?c, ?h), treats(?m, ?s)
-> herbContributesToTreating(?h, ?s)
```

---

## 6. Complex Medicine Classification (ยาตำรับที่ซับซ้อน vs ยาเดี่ยว)

**แนวคิด:** ถ้ายา (?m) มีส่วนประกอบ 2 ตัวขึ้นไป (มีส่วนประกอบ ?c1 และ ?c2 ที่ไม่ใช่ตัวเดียวกัน) แสดงว่าเป็นยาตำรับที่ซับซ้อน (Compound Formula)

**ประโยชน์:** สร้าง Data Property `isCompoundFormula` เพื่อแยกยาเดี่ยวออกจากยาตำรับผสม สะดวกในการจำแนกและนำเสนอข้อมูล

```
SWRL Rule:
HerbMedicine(?m) ∧ hasComponent(?m, ?c1) ∧ hasComponent(?m, ?c2) ∧ differentFrom(?c1, ?c2)
→ isCompoundFormula(?m, true)
```

**Protégé Syntax:**
```
HerbMedicine(?m), hasComponent(?m, ?c1), hasComponent(?m, ?c2), differentFrom(?c1, ?c2)
-> isCompoundFormula(?m, true)
```

---

## 7. Allergy-Based Contraindication Inference (ข้อห้ามจากการแพ้)

**แนวคิด:** ถ้ายา (?m) มี SafetyAlert ที่ triggeredBy AllergyCondition (?allergy) แสดงว่ายานั้นมีข้อจำกัดสำหรับผู้แพ้สารเฉพาะ

**ประโยชน์:** สร้าง Property `hasAllergyRestriction` เพื่อเชื่อมยากับสารก่อภูมิแพ้โดยตรง เพื่อใช้ในระบบตรวจสอบสิทธิ์การจ่ายยา

```
SWRL Rule:
HerbMedicine(?m) ∧ hasSafetyAlert(?m, ?a) ∧ Contraindication(?a) ∧ triggeredBy(?a, ?allergy) ∧ AllergyCondition(?allergy)
→ hasAllergyRestriction(?m, ?allergy)
```

**Protégé Syntax:**
```
HerbMedicine(?m), hasSafetyAlert(?m, ?a), Contraindication(?a), triggeredBy(?a, ?allergy), AllergyCondition(?allergy)
-> hasAllergyRestriction(?m, ?allergy)
```

---

## 8. Age-Restricted Medicine (การอนุมานข้อจำกัดอายุของยา)

**แนวคิด:** ถ้ายา (?m) มี SafetyAlert ที่ triggeredBy AgeCondition (?age) ที่มี maxAge น้อยกว่า 12 แสดงว่ายานั้นมีข้อจำกัดในเด็ก

**ประโยชน์:** สร้าง Data Property `hasChildRestriction` เพื่อ Flag ยาที่ต้องระวังในกลุ่มเด็ก

```
SWRL Rule:
HerbMedicine(?m) ∧ hasSafetyAlert(?m, ?a) ∧ triggeredBy(?a, ?age) ∧ AgeCondition(?age) ∧ maxAge(?age, ?maxA) ∧ swrlb:lessThan(?maxA, 12)
→ hasChildRestriction(?m, true)
```

**Protégé Syntax:**
```
HerbMedicine(?m), hasSafetyAlert(?m, ?a), triggeredBy(?a, ?age), AgeCondition(?age), maxAge(?age, ?maxA), swrlb:lessThan(?maxA, 12)
-> hasChildRestriction(?m, true)
```

---

## 9. Shared Herb Inference (ยาที่มีส่วนผสมเหมือนกัน)

**แนวคิด:** ถ้ายา (?m1) และยา (?m2) มีสมุนไพร (?h) ชนิดเดียวกันเป็นส่วนประกอบ แสดงว่าทั้งสองตำรับมี "ส่วนผสมสมุนไพรร่วมกัน"

**ประโยชน์:** สร้าง Property `sharesHerbWith` ช่วยสร้างเครือข่ายความเกี่ยวข้องระหว่างตำรับยาช่วยในการค้นหายาทดแทน

```
SWRL Rule:
HerbMedicine(?m1) ∧ HerbMedicine(?m2) ∧ hasComponent(?m1, ?c1) ∧ usesHerb(?c1, ?h)
∧ hasComponent(?m2, ?c2) ∧ usesHerb(?c2, ?h) ∧ differentFrom(?m1, ?m2)
→ sharesHerbWith(?m1, ?m2)
```

**Protégé Syntax:**
```
HerbMedicine(?m1), HerbMedicine(?m2), hasComponent(?m1, ?c1), usesHerb(?c1, ?h), hasComponent(?m2, ?c2), usesHerb(?c2, ?h), differentFrom(?m1, ?m2)
-> sharesHerbWith(?m1, ?m2)
```

---

## 10. High-Risk Medicine Classification (การจำแนกยาเสี่ยงสูง)

**แนวคิด:** ถ้ายา (?m) มีทั้งข้อห้ามสำหรับ "หญิงตั้งครรภ์" และมีข้อห้ามสำหรับ "ผู้มีไข้" แสดงว่ายานั้นเป็นยา "ความเสี่ยงสูง" ที่ต้องตรวจสอบเงื่อนไขประวัติผู้ป่วยก่อนจ่ายยาเสมอ

**ประโยชน์:** สร้าง Data Property `isHighRiskMedicine` สำหรับ Monitoring ในระบบคัดกรองการจ่ายยา

```
SWRL Rule:
HerbMedicine(?m) ∧ hasSafetyAlert(?m, ?a1) ∧ Contraindication(?a1) ∧ triggeredBy(?a1, hm:physio_ตั้งครรภ์)
∧ hasSafetyAlert(?m, ?a2) ∧ Contraindication(?a2) ∧ triggeredBy(?a2, hm:physio_มีไข้)
→ isHighRiskMedicine(?m, true)
```

**Protégé Syntax:**
```
HerbMedicine(?m), hasSafetyAlert(?m, ?a1), Contraindication(?a1), triggeredBy(?a1, hm:physio_ตั้งครรภ์), hasSafetyAlert(?m, ?a2), Contraindication(?a2), triggeredBy(?a2, hm:physio_มีไข้)
-> isHighRiskMedicine(?m, true)
```

---

## 11. Caution-Only Medicine (ยาที่มีเฉพาะข้อควรระวัง ไม่มีข้อห้ามใช้)

**แนวคิด:** ถ้ายา (?m) มี SafetyAlert ที่เป็น Caution แต่ไม่มี SafetyAlert ที่เป็น Contraindication เลย แสดงว่ายานั้นจัดว่า "ปลอดภัยสัมพัทธ์" (Relatively Safe)

**ประโยชน์:** สร้าง Data Property `isCautionOnly` สำหรับระบบแนะนำยาที่มีความเสี่ยงต่ำ

```
SWRL Rule:
HerbMedicine(?m) ∧ hasSafetyAlert(?m, ?a) ∧ Caution(?a)
→ hasCautionAlert(?m, true)
```

**Protégé Syntax:**
```
HerbMedicine(?m), hasSafetyAlert(?m, ?a), Caution(?a)
-> hasCautionAlert(?m, true)
```

---

## 12. Multi-System Treatment Inference (ยาที่รักษาได้หลายระบบ)

**แนวคิด:** ถ้ายา (?m) รักษาทั้ง Disease และ Symptom พร้อมกัน แสดงว่ายานั้นครอบคลุมการรักษาหลายมิติ (Multi-dimensional Treatment)

**ประโยชน์:** สร้าง Data Property `isMultiDimensionalTreatment` เพื่อจำแนกยาที่มีขอบเขตสรรพคุณกว้าง

```
SWRL Rule:
HerbMedicine(?m) ∧ treats(?m, ?d) ∧ Disease(?d) ∧ treats(?m, ?s) ∧ Symptom(?s)
→ isMultiDimensionalTreatment(?m, true)
```

**Protégé Syntax:**
```
HerbMedicine(?m), treats(?m, ?d), Disease(?d), treats(?m, ?s), Symptom(?s)
-> isMultiDimensionalTreatment(?m, true)
```

---

## วิธีนำไปใช้ใน Protégé

### ขั้นตอนที่ 1: สร้าง Properties ใหม่ที่จำเป็น
ก่อนเพิ่ม SWRL Rules ต้องสร้าง Properties ใหม่ลงใน Ontology ก่อน ดังนี้:

**Object Properties ใหม่ที่ต้องสร้าง:**
| Property Name | Domain | Range |
|---|---|---|
| `belongsToSystem` | `HerbMedicine` | `GroupMedicine` |
| `herbContributesToTreating` | `Herb` | `MedicalCondition` |
| `hasAllergyRestriction` | `HerbMedicine` | `AllergyCondition` |
| `sharesHerbWith` | `HerbMedicine` | `HerbMedicine` |

**Data Properties ใหม่ที่ต้องสร้าง:**
| Property Name | Domain | Range | Description |
|---|---|---|---|
| `isUnsafeForPregnancy` | `HerbMedicine` | `xsd:boolean` | ห้ามใช้ขณะตั้งครรภ์ |
| `isUnsafeForLactation` | `HerbMedicine` | `xsd:boolean` | ห้ามใช้ขณะให้นมบุตร |
| `isUnsafeDuringFever` | `HerbMedicine` | `xsd:boolean` | ห้ามใช้ขณะมีไข้ |
| `isCompoundFormula` | `HerbMedicine` | `xsd:boolean` | เป็นยาตำรับผสม |
| `hasChildRestriction` | `HerbMedicine` | `xsd:boolean` | มีข้อจำกัดในเด็ก |
| `isHighRiskMedicine` | `HerbMedicine` | `xsd:boolean` | ยาความเสี่ยงสูง |
| `hasCautionAlert` | `HerbMedicine` | `xsd:boolean` | มีเฉพาะข้อควรระวัง |
| `isMultiDimensionalTreatment` | `HerbMedicine` | `xsd:boolean` | รักษาได้หลายมิติ |

### ขั้นตอนที่ 2: เพิ่ม SWRL Rules ใน Protégé
1. เปิด Protégé → แท็บ **SWRLTab** (หรือ Window > Tabs > SWRLTab)
2. กดปุ่ม **New Rule** (ไอคอน +)
3. วาง Protégé Syntax ลงในช่อง Rule
4. ตั้งชื่อ Rule (เช่น `PregnancySafetyFlag`)
5. กด **OK**

### ขั้นตอนที่ 3: รัน Reasoner
1. ไปที่ Reasoner → เลือก **Pellet** (แนะนำ เพราะรองรับ SWRL)
2. กด **Start Reasoner** หรือ **Synchronize Reasoner**
3. ตรวจสอบผลลัพธ์ในแท็บ **Individuals** ของแต่ละ `HerbMedicine`
