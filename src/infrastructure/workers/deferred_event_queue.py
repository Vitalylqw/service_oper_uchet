"""
Deferred Event Queue for handling events that cannot be processed immediately.

Provides a robust mechanism for handling events that fail to process
due to missing dependencies or other temporary issues.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from collections import defaultdict

from loguru import logger


class DeferredEvent:
    """Represents an event that has been deferred for later processing."""
    
    def __init__(self, event: dict[str, Any], reason: str, retry_count: int = 0):
        self.event = event
        self.reason = reason
        self.retry_count = retry_count
        self.created_at = datetime.now()
        self.retry_after = self._calculate_retry_time()
        self.id = str(uuid.uuid4())
    
    def _calculate_retry_time(self) -> datetime:
        """Calculate when to retry based on retry count."""
        retry_delays = [5, 15, 60]  # minutes
        delay_minutes = retry_delays[min(self.retry_count, len(retry_delays) - 1)]
        return datetime.now() + timedelta(minutes=delay_minutes)
    
    def increment_retry(self) -> None:
        """Increment retry count and update retry time."""
        self.retry_count += 1
        self.retry_after = self._calculate_retry_time()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "id": self.id,
            "event_type": self.event.get("event_type"),
            "aggregate_id": str(self.event.get("aggregate_id")),
            "reason": self.reason,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "retry_after": self.retry_after.isoformat(),
        }


class DeferredEventMetrics:
    """Metrics collection for deferred events."""
    
    def __init__(self):
        self.deferred_count = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.permanent_failures = 0
        self.reasons = defaultdict(int)
        self.event_types = defaultdict(int)
    
    def record_deferred(self, event_type: str, reason: str) -> None:
        """Record a deferred event."""
        self.deferred_count += 1
        self.reasons[reason] += 1
        self.event_types[event_type] += 1
    
    def record_successful_retry(self) -> None:
        """Record a successful retry."""
        self.successful_retries += 1
    
    def record_failed_retry(self) -> None:
        """Record a failed retry."""
        self.failed_retries += 1
    
    def record_permanent_failure(self) -> None:
        """Record a permanent failure."""
        self.permanent_failures += 1
    
    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_deferred": self.deferred_count,
            "successful_retries": self.successful_retries,
            "failed_retries": self.failed_retries,
            "permanent_failures": self.permanent_failures,
            "reasons": dict(self.reasons),
            "event_types": dict(self.event_types),
        }


class DeferredEventQueue:
    """Queue for managing deferred events with retry logic."""
    
    def __init__(self, max_retries: int = 3):
        self.queue: List[DeferredEvent] = []
        self.max_retries = max_retries
        self.metrics = DeferredEventMetrics()
    
    async def add_event(self, event: dict[str, Any], reason: str) -> None:
        """
        Add an event to the deferred queue.
        
        Args:
            event: The event that failed to process
            reason: Human-readable reason for deferral
        """
        deferred = DeferredEvent(event, reason)
        self.queue.append(deferred)
        
        event_type = event.get("event_type", "Unknown")
        self.metrics.record_deferred(event_type, reason)
        
        logger.warning(
            f"Event deferred: {event_type} for {event.get('aggregate_id')} - {reason}"
        )
        logger.debug(f"Deferred event details: {deferred.to_dict()}")
    
    async def process_deferred_events(self, processor_func) -> int:
        """
        Process deferred events that are ready for retry.
        
        Args:
            processor_func: Function to process a single event
            
        Returns:
            Number of events successfully processed
        """
        current_time = datetime.now()
        ready_events = [
            e for e in self.queue 
            if e.retry_after <= current_time and e.retry_count < self.max_retries
        ]
        
        processed_count = 0
        
        for deferred in ready_events:
            try:
                logger.info(
                    f"Retrying deferred event: {deferred.event.get('event_type')} "
                    f"(attempt {deferred.retry_count + 1}/{self.max_retries})"
                )
                
                await processor_func(deferred.event)
                
                # Success - remove from queue
                self.queue.remove(deferred)
                self.metrics.record_successful_retry()
                processed_count += 1
                
                logger.info(
                    f"Successfully processed deferred event: {deferred.event.get('event_type')}"
                )
                
            except Exception as e:
                deferred.increment_retry()
                self.metrics.record_failed_retry()
                
                if deferred.retry_count >= self.max_retries:
                    # Permanent failure
                    self.queue.remove(deferred)
                    self.metrics.record_permanent_failure()
                    
                    logger.error(
                        f"Event failed permanently after {self.max_retries} retries: "
                        f"{deferred.event.get('event_type')} - {deferred.reason}"
                    )
                    logger.error(f"Final error: {e}")
                else:
                    logger.warning(
                        f"Deferred event retry failed: {deferred.event.get('event_type')} "
                        f"(attempt {deferred.retry_count}/{self.max_retries}) - {e}"
                    )
        
        return processed_count
    
    def get_queue_status(self) -> dict[str, Any]:
        """Get current queue status."""
        return {
            "queue_size": len(self.queue),
            "ready_for_retry": len([
                e for e in self.queue 
                if e.retry_after <= datetime.now() and e.retry_count < self.max_retries
            ]),
            "metrics": self.metrics.get_summary(),
        }
    
    def clear_queue(self) -> None:
        """Clear all deferred events (for testing/debugging)."""
        cleared_count = len(self.queue)
        self.queue.clear()
        logger.info(f"Cleared {cleared_count} deferred events from queue")
    
    def get_deferred_events_summary(self) -> List[dict[str, Any]]:
        """Get summary of all deferred events for debugging."""
        return [event.to_dict() for event in self.queue]