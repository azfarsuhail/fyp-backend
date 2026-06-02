"""
Mobile Sync Service
-------------------
Handles syncing user-specific data to mobile devices.
Only syncs the authenticated user's data, not the entire database.

Data Synced:
- User profile (age, pain_level, mobility_level, has_support)
- User's uploaded images
- User's diagnostic reports
- User's profile change history
- User's exercise video preferences (if any)

Data NOT Synced:
- Other users' data
- Exercise video library (downloaded separately if needed)
- System-wide configurations
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import json
import sqlite3
from pathlib import Path
from app.services.s3_service import generate_presigned_url


class MobileSyncService:
    """Service for syncing user data to mobile devices."""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
    
    def get_user_data(self) -> Dict[str, Any]:
        """
        Gather all user-specific data for sync.
        
        Returns:
            Dictionary containing all user data organized by type
        """
        from app.models.user import User
        from app.models.image import Image
        from app.models.report import Report
        from app.models.profile_log import ProfileLog
        
        # Get user profile
        user = self.db.query(User).filter(User.user_id == self.user_id).first()
        if not user:
            raise ValueError(f"User {self.user_id} not found")
        
        # Get user's images
        images = self.db.query(Image).filter(Image.user_id == self.user_id).all()
        images_data = [
            {
                "image_id": img.image_id,
                "s3_url": generate_presigned_url(img.s3_url) if img.s3_url else None,
                "processed_s3_url": generate_presigned_url(img.processed_s3_url) if img.processed_s3_url else None,
                "file_name": img.file_name,
                "content_type": img.content_type,
                "uploaded_at": img.uploaded_at.isoformat() if img.uploaded_at else None,
            }
            for img in images
        ]
        
        # Get user's reports
        reports = self.db.query(Report).filter(Report.user_id == self.user_id).all()
        reports_data = [
            {
                "report_id": rpt.report_id,
                "image_id": rpt.image_id,
                "kl_grade": rpt.kl_grade,
                "confidence": rpt.confidence,
                "diagnosis_summary": rpt.diagnosis_summary,
                "recommendation": rpt.recommendation,
                "lifestyle_plan": json.loads(rpt.lifestyle_plan) if rpt.lifestyle_plan else [],
                "warnings": json.loads(rpt.warnings) if rpt.warnings else [],
                "exercise_video_urls": json.loads(rpt.exercise_video_urls) if rpt.exercise_video_urls else [],
                "created_at": rpt.created_at.isoformat() if rpt.created_at else None,
            }
            for rpt in reports
        ]
        
        # Get user's profile history
        history = self.db.query(ProfileLog).filter(
            ProfileLog.user_id == self.user_id
        ).order_by(ProfileLog.changed_at.desc()).all()
        history_data = [
            {
                "log_id": log.log_id,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "changed_at": log.changed_at.isoformat() if log.changed_at else None,
            }
            for log in history
        ]
        
        return {
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "age": user.age,
                "pain_level": user.pain_level,
                "mobility_level": user.mobility_level,
                "has_support": user.has_support,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
            "images": images_data,
            "reports": reports_data,
            "history": history_data,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def export_to_json(self, output_path: Optional[str] = None) -> str:
        """
        Export user data to JSON file.
        
        Args:
            output_path: Optional path to save JSON file. If None, returns string.
        
        Returns:
            JSON string of user data
        """
        user_data = self.get_user_data()
        json_str = json.dumps(user_data, indent=2, default=str)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str
    
    def create_mobile_db(self, db_path: str) -> None:
        """
        Create a local SQLite database with user data.
        
        Args:
            db_path: Path to the SQLite database file
        """
        user_data = self.get_user_data()
        
        # Connect to SQLite database (creates if doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                user_id INTEGER PRIMARY KEY,
                email TEXT,
                full_name TEXT,
                role TEXT,
                age INTEGER,
                pain_level INTEGER,
                mobility_level TEXT,
                has_support INTEGER,
                created_at TEXT,
                last_login TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                image_id INTEGER PRIMARY KEY,
                s3_url TEXT,
                processed_s3_url TEXT,
                file_name TEXT,
                content_type TEXT,
                uploaded_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                report_id INTEGER PRIMARY KEY,
                image_id INTEGER,
                kl_grade INTEGER,
                confidence REAL,
                diagnosis_summary TEXT,
                recommendation TEXT,
                lifestyle_plan TEXT,
                warnings TEXT,
                exercise_video_urls TEXT,
                created_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile_history (
                log_id INTEGER PRIMARY KEY,
                field_name TEXT,
                old_value TEXT,
                new_value TEXT,
                changed_at TEXT
            )
        ''')
        
        # Insert user profile
        user = user_data['user']
        cursor.execute('''
            INSERT OR REPLACE INTO user_profile 
            (user_id, email, full_name, role, age, pain_level, mobility_level, has_support, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user['user_id'], user['email'], user['full_name'], user['role'],
            user['age'], user['pain_level'], user['mobility_level'],
            user['has_support'], user['created_at'], user['last_login']
        ))
        
        # Insert images
        for img in user_data['images']:
            cursor.execute('''
                INSERT OR REPLACE INTO images 
                (image_id, s3_url, processed_s3_url, file_name, content_type, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                img['image_id'], img['s3_url'], img['processed_s3_url'],
                img['file_name'], img['content_type'], img['uploaded_at']
            ))
        
        # Insert reports
        for rpt in user_data['reports']:
            cursor.execute('''
                INSERT OR REPLACE INTO reports 
                (report_id, image_id, kl_grade, confidence, diagnosis_summary, 
                 recommendation, lifestyle_plan, warnings, exercise_video_urls, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rpt['report_id'], rpt['image_id'], rpt['kl_grade'], rpt['confidence'],
                rpt['diagnosis_summary'], rpt['recommendation'],
                json.dumps(rpt['lifestyle_plan']), json.dumps(rpt['warnings']),
                json.dumps(rpt['exercise_video_urls']), rpt['created_at']
            ))
        
        # Insert history
        for log in user_data['history']:
            cursor.execute('''
                INSERT OR REPLACE INTO profile_history 
                (log_id, field_name, old_value, new_value, changed_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                log['log_id'], log['field_name'], log['old_value'],
                log['new_value'], log['changed_at']
            ))
        
        conn.commit()
        conn.close()
    
    def get_sync_summary(self) -> Dict[str, Any]:
        """
        Get a summary of data that will be synced.
        
        Returns:
            Dictionary with counts and metadata
        """
        from app.models.image import Image
        from app.models.report import Report
        from app.models.profile_log import ProfileLog
        
        image_count = self.db.query(Image).filter(Image.user_id == self.user_id).count()
        report_count = self.db.query(Report).filter(Report.user_id == self.user_id).count()
        history_count = self.db.query(ProfileLog).filter(
            ProfileLog.user_id == self.user_id
        ).count()
        
        return {
            "user_id": self.user_id,
            "images_count": image_count,
            "reports_count": report_count,
            "history_count": history_count,
            "total_records": image_count + report_count + history_count,
        }


def sync_user_data(db: Session, user_id: int, output_path: Optional[str] = None) -> str:
    """
    Convenience function to sync user data.
    
    Args:
        db: Database session
        user_id: ID of the user to sync
        output_path: Optional path to save SQLite database
    
    Returns:
        JSON string of user data
    """
    sync_service = MobileSyncService(db, user_id)
    
    if output_path:
        sync_service.create_mobile_db(output_path)
    
    return sync_service.export_to_json()
