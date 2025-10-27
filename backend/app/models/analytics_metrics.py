"""
class TicketProcessingMetrics(Base):
    id
    ticket_id on delete cascade
    processing_started_at = Timestamp
    processsing_completed_at = Timestamp
    processing_duration integer
    analysis duration integer
    
"""