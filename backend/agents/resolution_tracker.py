"""
MedClaim — Resolution Tracker Agent

Background agent running as a Celery periodic task (every 4 hours).
Monitors SUBMITTED and APPEAL_SUBMITTED claims for staleness and
approaching appeal deadlines. Sends email alerts via Resend.
Writes resolved claim outcomes back into the denial_patterns Qdrant
collection (feedback loop).

Implementation: Subphase 4.1
"""
