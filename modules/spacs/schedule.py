"""Celery beat schedule and task routes for SPACS."""

from celery.schedules import crontab

TASK_ROUTES = {
    "spacs.deliver_notifications": {"queue": "notifications"},
    "spacs.check_review_slas": {"queue": "default"},
    "spacs.send_renewal_reminders": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "spacs.deliver-notifications": {
        "task": "spacs.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "spacs.check-review-slas": {
        "task": "spacs.check_review_slas",
        "schedule": crontab(hour="7", minute="0"),
        "options": {"expires": 3600},
    },
    "spacs.send-renewal-reminders": {
        "task": "spacs.send_renewal_reminders",
        "schedule": crontab(hour="8", minute="0"),
        "options": {"expires": 3600},
    },
}
