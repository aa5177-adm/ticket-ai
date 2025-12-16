import json
import logging
from typing import Optional
from google.cloud import pubsub_v1
from google.api_core import exceptions
from app.core.config import settings

logger = logging.getLogger(__name__)

class TicketPublisher:
    """Publisher for sending ticket data to Google Cloud Pub/Sub"""
    
    def __init__(self):
        """Initialize the Pub/Sub publisher client"""
        try:
            self.project_id = settings.GCP_PROJECT_ID
            self.topic_id = settings.PUBSUB_TOPIC_ID
            self.max_retries = settings.MAX_RETRIES
            self.timeout = settings.PUBLISH_TIMEOUT
            
            # Initialize publisher client with custom settings
            self.publisher = pubsub_v1.PublisherClient()
            self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
            
            logger.info(
                f"TicketPublisher initialized - Project: {self.project_id}, "
                f"Topic: {self.topic_id}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize TicketPublisher: {e}")
            raise

    def verify_connection(self) -> bool:
        """
        Verify connection to Pub/Sub topic.
        
        Returns:
            bool: True if connection is successful
            
        Raises:
            Exception: If connection verification fails
        """
        try:
            # Check if topic exists
            self.publisher.get_topic(request={"topic": self.topic_path})
            logger.info(f"Successfully verified connection to topic: {self.topic_path}")
            return True
        except exceptions.NotFound:
            logger.error(f"Topic not found: {self.topic_path}")
            raise Exception(f"Pub/Sub topic '{self.topic_id}' does not exist")
        except exceptions.PermissionDenied:
            logger.error(f"Permission denied accessing topic: {self.topic_path}")
            raise Exception("Insufficient permissions to access Pub/Sub topic")
        except Exception as e:
            logger.error(f"Failed to verify Pub/Sub connection: {e}")
            raise

    def publish_ticket(
        self,
        ticket_data: dict,
        webhook_id: Optional[str] = None,
        
    ) -> str:
        """
        Publish ticket data to Google Cloud Pub/Sub topic with retry logic.

        Args:
            ticket_data: The ticket data to publish
            attributes: Optional message attributes for routing/filtering

        Returns:
            str: The message ID of the published message
            
        Raises:
            Exception: If publishing fails after retries
        """
        try:
            # Convert ticket data to JSON and encode
            message_json = json.dumps(ticket_data, ensure_ascii=False)
            message_bytes = message_json.encode('utf-8')
            
            # Prepare message attributes
            message_attributes = {}
            if webhook_id:
                message_attributes["webhook_id"] = webhook_id


            # Publish with retry logic
            future = self.publisher.publish(
                self.topic_path,
                data=message_bytes,
                **message_attributes
            )
            
            # Wait for publish to complete with timeout
            message_id = future.result(timeout=self.timeout)
            
            logger.info(
                f"Successfully published ticket '{ticket_data.get('number')}' "
                f"with message ID: {message_id}"
            )
            
            return message_id
            
        except exceptions.GoogleAPICallError as e:
            logger.error(
                f"Google API error publishing ticket '{ticket_data.get('number')}': {e}",
                exc_info=True
            )
            raise Exception(f"Failed to publish message to Pub/Sub: {e}")
        except TimeoutError as e:
            logger.error(
                f"Timeout publishing ticket '{ticket_data.get('number')}': {e}"
            )
            raise Exception(f"Pub/Sub publish timeout after {self.timeout}s")
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in ticket data '{ticket_data.get('number')}': {e}"
            )
            raise Exception(f"Invalid ticket data format: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error publishing ticket '{ticket_data.get('number')}': {e}",
                exc_info=True
            )
            raise
    
    def __del__(self):
        """Cleanup publisher client on deletion"""
        try:
            if hasattr(self, 'publisher'):
                # No explicit close needed for PublisherClient
                pass
        except Exception as e:
            logger.error(f"Error during publisher cleanup: {e}")