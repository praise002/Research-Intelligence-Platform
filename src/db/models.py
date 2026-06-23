"""
This file serves as an aggregation point for all SQLAlchemy models across the application.
Alembic uses this file to detect schema changes when generating migrations.

Import every model from each of your application's 'models.py' files here.
"""

from src.alerts.models import Alert
from src.auth.models import User
from src.competitors.models import Competitor, CompetitorSource
from src.reports.models import Feedback, Report
from src.research.models import Job
from src.schedule.models import Schedule

__all__ = [
    "User",
    "Competitor",
    "CompetitorSource",
    "Alert",
    "Report",
    "Feedback",
    "Job",
    "Schedule",
]
