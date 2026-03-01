import uuid
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import ClassificationRuleCreate, ClassificationRuleResponse
from app.models.db_models import ClassificationRuleModel
from app.core.database import get_db

router = APIRouter(prefix="/classifications", tags=["Data Classification"])

DEFAULT_RULES = [
    {"name": "Social Security Number", "category": "PII", "pattern": r"\b\d{3}-\d{2}-\d{4}\b", "keywords": ["social security", "ssn"]},
    {"name": "Credit Card Number", "category": "PCI", "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "keywords": ["credit card", "card number", "pan"]},
    {"name": "Email Address", "category": "PII", "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "keywords": ["email"]},
    {"name": "Medical Record Number", "category": "PHI", "pattern": r"\b(?:MRN|mrn)[\s:#-]?\d{4,10}\b", "keywords": ["medical record", "mrn"]},
    {"name": "ICD-10 Code", "category": "PHI", "pattern": r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b", "keywords": ["icd", "diagnosis code"]},
    {"name": "Phone Number", "category": "PII", "pattern": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "keywords": ["phone", "telephone"]},
    {"name": "Date of Birth", "category": "PII", "pattern": r"\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b", "keywords": ["date of birth", "dob", "birthday"]},
    {"name": "API Key", "category": "CUSTOM", "pattern": r"\b(?:sk-|pk_|api[_-]?key)[A-Za-z0-9_-]{20,}\b", "keywords": ["api key", "secret key"]},
]


async def seed_classification_rules(db: AsyncSession):
    result = await db.execute(select(ClassificationRuleModel))
    if result.scalars().first():
        return
    for rule in DEFAULT_RULES:
        db.add(ClassificationRuleModel(**rule))
    await db.commit()


@router.get("", response_model=list[ClassificationRuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ClassificationRuleModel))
    rows = result.scalars().all()
    return [ClassificationRuleResponse(
        id=str(r.id), name=r.name, category=r.category,
        pattern=r.pattern, keywords=r.keywords or [],
        enabled=r.enabled, created_at=r.created_at,
    ) for r in rows]


@router.post("", response_model=ClassificationRuleResponse)
async def create_rule(data: ClassificationRuleCreate, db: AsyncSession = Depends(get_db)):
    model = ClassificationRuleModel(
        name=data.name, category=data.category.value,
        pattern=data.pattern, keywords=data.keywords, enabled=data.enabled,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return ClassificationRuleResponse(
        id=str(model.id), name=model.name, category=model.category,
        pattern=model.pattern, keywords=model.keywords or [],
        enabled=model.enabled, created_at=model.created_at,
    )


@router.put("/{rule_id}", response_model=ClassificationRuleResponse)
async def update_rule(rule_id: str, data: ClassificationRuleCreate,
                      db: AsyncSession = Depends(get_db)):
    row = await db.get(ClassificationRuleModel, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    row.name = data.name
    row.category = data.category.value
    row.pattern = data.pattern
    row.keywords = data.keywords
    row.enabled = data.enabled
    await db.commit()
    await db.refresh(row)
    return ClassificationRuleResponse(
        id=str(row.id), name=row.name, category=row.category,
        pattern=row.pattern, keywords=row.keywords or [],
        enabled=row.enabled, created_at=row.created_at,
    )


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(ClassificationRuleModel, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(row)
    await db.commit()
    return {"status": "deleted"}


@router.post("/test")
async def test_classification(payload: dict, request: Request):
    """Test classification using regex patterns from DB rules + built-in PII detector.
    Unlike the full CIL pipeline, this skips Luhn validation so users can test patterns."""
    import re
    text = payload.get("text", "")

    # 1) Match against DB classification rules (pure regex, no Luhn)
    db_rules = []
    try:
        from sqlalchemy import select as sa_select
        from app.core.database import async_session
        async with async_session() as db:
            result = await db.execute(sa_select(ClassificationRuleModel).where(
                ClassificationRuleModel.enabled == True
            ))
            db_rules = result.scalars().all()
    except Exception:
        pass

    classifications = set()
    entities = []
    for rule in db_rules:
        if rule.pattern:
            for match in re.finditer(rule.pattern, text, re.IGNORECASE):
                classifications.add(rule.category)
                entities.append({
                    "type": rule.name,
                    "value": match.group(),
                    "position": [match.start(), match.end()],
                    "confidence": 1.0,
                    "rule_id": str(rule.id),
                })
        if rule.keywords:
            text_lower = text.lower()
            matched_kw = [kw for kw in rule.keywords if kw.lower() in text_lower]
            if matched_kw:
                classifications.add(rule.category)

    # 2) Also run the built-in PII detector (includes keyword scoring)
    from app.services.context_detector import PIIDetector
    pii = PIIDetector()
    pii_entities, _ = pii.scan(text)
    for e in pii_entities:
        if not any(x["value"] == e.value and x["type"] == e.type for x in entities):
            entities.append(e.model_dump())

    return {
        "classifications": sorted(classifications),
        "entities": entities,
    }
