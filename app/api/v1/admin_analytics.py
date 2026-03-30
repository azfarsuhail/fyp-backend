"""
Admin Analytics Router
----------------------
API endpoints for admin dashboard analytics and statistics.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, List, Any

from app.core.dependencies import get_db, RoleChecker
from app.models.user import User
from app.models.image import Image
from app.models.report import Report
from app.models.profile_log import ProfileLog

router = APIRouter()

# Only admins can access analytics
allow_admin = RoleChecker(allowed_roles=["admin"])


@router.get("/analytics/dashboard")
def get_dashboard_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_admin),
):
    """
    Get comprehensive dashboard analytics.
    
    Returns:
        Dictionary with all dashboard statistics
    """
    # Total users
    total_users = db.query(func.count(User.user_id)).scalar()
    
    # Users by role
    users_by_role = db.query(
        User.role, 
        func.count(User.user_id)
    ).group_by(User.role).all()
    users_by_role_dict = {role: count for role, count in users_by_role}
    
    # New users this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_this_week = db.query(func.count(User.user_id)).filter(
        User.created_at >= week_ago
    ).scalar()
    
    # New users this month
    month_ago = datetime.utcnow() - timedelta(days=30)
    new_users_this_month = db.query(func.count(User.user_id)).filter(
        User.created_at >= month_ago
    ).scalar()
    
    # Total images uploaded
    total_images = db.query(func.count(Image.image_id)).scalar()
    
    # Images this week
    images_this_week = db.query(func.count(Image.image_id)).filter(
        Image.uploaded_at >= week_ago
    ).scalar()
    
    # Total reports generated
    total_reports = db.query(func.count(Report.report_id)).scalar()
    
    # Reports this week
    reports_this_week = db.query(func.count(Report.report_id)).filter(
        Report.created_at >= week_ago
    ).scalar()
    
    # Average KL grade distribution
    kl_distribution = db.query(
        Report.kl_grade,
        func.count(Report.report_id)
    ).group_by(Report.kl_grade).all()
    kl_distribution_dict = {grade: count for grade, count in kl_distribution}
    
    # Average confidence score
    avg_confidence = db.query(func.avg(Report.confidence)).scalar() or 0
    
    # Profile changes this week (activity metric)
    profile_changes_this_week = db.query(func.count(ProfileLog.log_id)).filter(
        ProfileLog.changed_at >= week_ago
    ).scalar()
    
    # Recent activity (last 10 reports)
    recent_reports = db.query(Report).order_by(
        Report.created_at.desc()
    ).limit(10).all()
    
    recent_activity = [
        {
            "report_id": rpt.report_id,
            "user_id": rpt.user_id,
            "kl_grade": rpt.kl_grade,
            "confidence": rpt.confidence,
            "created_at": rpt.created_at.isoformat() if rpt.created_at else None,
        }
        for rpt in recent_reports
    ]
    
    # User growth (last 7 days)
    user_growth = []
    for i in range(6, -1, -1):
        date = datetime.utcnow() - timedelta(days=i)
        date_end = date + timedelta(days=1)
        count = db.query(func.count(User.user_id)).filter(
            User.created_at >= date,
            User.created_at < date_end
        ).scalar()
        user_growth.append({
            "date": date.strftime("%Y-%m-%d"),
            "new_users": count
        })
    
    # System health
    system_health = {
        "total_users": total_users,
        "total_images": total_images,
        "total_reports": total_reports,
        "avg_confidence": round(avg_confidence, 2),
        "status": "healthy"
    }
    
    return {
        "overview": {
            "total_users": total_users,
            "users_by_role": users_by_role_dict,
            "new_users_this_week": new_users_this_week,
            "new_users_this_month": new_users_this_month,
            "total_images": total_images,
            "images_this_week": images_this_week,
            "total_reports": total_reports,
            "reports_this_week": reports_this_week,
            "profile_changes_this_week": profile_changes_this_week,
        },
        "kl_distribution": kl_distribution_dict,
        "user_growth": user_growth,
        "recent_activity": recent_activity,
        "system_health": system_health,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/analytics/users")
def get_user_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_admin),
):
    """
    Get detailed user analytics.
    
    Returns:
        Dictionary with user statistics
    """
    # Total users
    total_users = db.query(func.count(User.user_id)).scalar()
    
    # Active users (logged in last 30 days)
    month_ago = datetime.utcnow() - timedelta(days=30)
    active_users = db.query(func.count(User.user_id)).filter(
        User.last_login >= month_ago
    ).scalar()
    
    # Users by role
    users_by_role = db.query(
        User.role,
        func.count(User.user_id)
    ).group_by(User.role).all()
    
    # Average pain level across all users
    avg_pain_level = db.query(func.avg(User.pain_level)).scalar() or 0
    
    # Users with support
    users_with_support = db.query(func.count(User.user_id)).filter(
        User.has_support == True
    ).scalar()
    
    # Users without support
    users_without_support = db.query(func.count(User.user_id)).filter(
        User.has_support == False
    ).scalar()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "active_percentage": round((active_users / total_users * 100), 1) if total_users > 0 else 0,
        "users_by_role": {role: count for role, count in users_by_role},
        "avg_pain_level": round(avg_pain_level, 1),
        "users_with_support": users_with_support,
        "users_without_support": users_without_support,
    }


@router.get("/analytics/reports")
def get_report_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_admin),
):
    """
    Get report analytics.
    
    Returns:
        Dictionary with report statistics
    """
    # Total reports
    total_reports = db.query(func.count(Report.report_id)).scalar()
    
    # Reports by KL grade
    reports_by_grade = db.query(
        Report.kl_grade,
        func.count(Report.report_id)
    ).group_by(Report.kl_grade).all()
    
    # Average confidence
    avg_confidence = db.query(func.avg(Report.confidence)).scalar() or 0
    
    # Confidence distribution
    high_confidence = db.query(func.count(Report.report_id)).filter(
        Report.confidence >= 0.8
    ).scalar()
    
    medium_confidence = db.query(func.count(Report.report_id)).filter(
        Report.confidence >= 0.6,
        Report.confidence < 0.8
    ).scalar()
    
    low_confidence = db.query(func.count(Report.report_id)).filter(
        Report.confidence < 0.6
    ).scalar()
    
    # Reports this month
    month_ago = datetime.utcnow() - timedelta(days=30)
    reports_this_month = db.query(func.count(Report.report_id)).filter(
        Report.created_at >= month_ago
    ).scalar()
    
    return {
        "total_reports": total_reports,
        "reports_by_grade": {grade: count for grade, count in reports_by_grade},
        "avg_confidence": round(avg_confidence, 2),
        "high_confidence": high_confidence,
        "medium_confidence": medium_confidence,
        "low_confidence": low_confidence,
        "reports_this_month": reports_this_month,
    }


@router.get("/analytics/activity")
def get_activity_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(allow_admin),
):
    """
    Get activity analytics.
    
    Returns:
        Dictionary with activity statistics
    """
    # Profile changes this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    profile_changes = db.query(func.count(ProfileLog.log_id)).filter(
        ProfileLog.changed_at >= week_ago
    ).scalar()
    
    # Profile changes by field
    changes_by_field = db.query(
        ProfileLog.field_name,
        func.count(ProfileLog.log_id)
    ).filter(
        ProfileLog.changed_at >= week_ago
    ).group_by(ProfileLog.field_name).all()
    
    # Recent uploads (last 7 days)
    images_this_week = db.query(func.count(Image.image_id)).filter(
        Image.uploaded_at >= week_ago
    ).scalar()
    
    # Recent reports (last 7 days)
    reports_this_week = db.query(func.count(Report.report_id)).filter(
        Report.created_at >= week_ago
    ).scalar()
    
    return {
        "profile_changes_this_week": profile_changes,
        "changes_by_field": {field: count for field, count in changes_by_field},
        "images_this_week": images_this_week,
        "reports_this_week": reports_this_week,
    }
