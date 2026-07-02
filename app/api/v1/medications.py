from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, RoleChecker
from app.schemas.recommendation_schema import Medication
from app.services.medication_service import create_medication, list_medications

router = APIRouter()

allow_admin = RoleChecker(allowed_roles=["admin"])


class MedicationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    dosage: str
    frequency: str
    instructions: Optional[str] = None
    contraindications: Optional[List[str]] = None
    kl_grade_min: int = Field(..., ge=0, le=4)
    kl_grade_max: int = Field(..., ge=0, le=4)

    @model_validator(mode="after")
    def validate_grade_range(self):
        if self.kl_grade_min > self.kl_grade_max:
            raise ValueError("kl_grade_min must be less than or equal to kl_grade_max")
        return self


@router.get("/medications/", response_model=List[Medication])
def get_medications(db: Session = Depends(get_db)):
    return list_medications(db)


@router.post("/admin/medications/", response_model=Medication, status_code=status.HTTP_201_CREATED)
def add_medication(
    medication: MedicationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_admin),
):
    return create_medication(db, medication.model_dump())