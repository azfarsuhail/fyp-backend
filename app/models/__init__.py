# Models package - exports all models for proper SQLAlchemy registration
from app.models.user import User
from app.models.image import Image
from app.models.report import Report
from app.models.library import ExerciseVideo
from app.models.profile_log import ProfileLog
from app.models.otp_verification import OTPVerification

__all__ = ["User", "Image", "Report", "ExerciseVideo", "ProfileLog", "OTPVerification"]
