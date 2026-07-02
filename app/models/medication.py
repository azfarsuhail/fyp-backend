from sqlalchemy import Column, Integer, String, Text, CheckConstraint

from app.core.config import Base


class MedicationModel(Base):
    __tablename__ = "MEDICATION"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    instructions = Column(Text, nullable=True)
    contraindications = Column(Text, nullable=True)
    kl_grade_min = Column(Integer, nullable=False)
    kl_grade_max = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("kl_grade_min >= 0 AND kl_grade_min <= 4", name="ck_medication_kl_grade_min"),
        CheckConstraint("kl_grade_max >= 0 AND kl_grade_max <= 4", name="ck_medication_kl_grade_max"),
        CheckConstraint("kl_grade_min <= kl_grade_max", name="ck_medication_kl_grade_order"),
    )