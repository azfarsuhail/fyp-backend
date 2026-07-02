import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.medication import MedicationModel
from app.schemas.recommendation_schema import Medication


def _parse_contraindications(value: Optional[str]) -> Optional[List[str]]:
    if value is None:
        return None

    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]

    cleaned = value.strip() if isinstance(value, str) else str(value).strip()
    if not cleaned:
        return None

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return [cleaned]

    if parsed is None:
        return None
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return [str(parsed)]


def medication_to_schema(record: MedicationModel) -> Medication:
    return Medication(
        id=record.id,
        name=record.name,
        dosage=record.dosage,
        frequency=record.frequency,
        instructions=record.instructions,
        contraindications=_parse_contraindications(record.contraindications),
        kl_grade_min=record.kl_grade_min,
        kl_grade_max=record.kl_grade_max,
    )


def list_medications(db: Session) -> List[Medication]:
    records = db.query(MedicationModel).order_by(MedicationModel.name.asc(), MedicationModel.id.asc()).all()
    return [medication_to_schema(record) for record in records]


def create_medication(db: Session, payload: Dict[str, Any]) -> Medication:
    contraindications = payload.get("contraindications")
    if contraindications is not None:
        contraindications = json.dumps(contraindications)

    record = MedicationModel(
        name=payload["name"],
        dosage=payload["dosage"],
        frequency=payload["frequency"],
        instructions=payload.get("instructions"),
        contraindications=contraindications,
        kl_grade_min=payload["kl_grade_min"],
        kl_grade_max=payload["kl_grade_max"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return medication_to_schema(record)