import requests
from typing import Dict, Any
from src.webhook_service.wa_models.message_models import WhatsAppMessageRequest


class WhatsAppClient:
    """WhatsApp Cloud API client"""
    
    def __init__(self, access_token: str, phone_number_id: str, api_version: str = "v23.0"):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    
    def send_message(self, message: WhatsAppMessageRequest) -> Dict[str, Any]:
        """Send WhatsApp message"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        payload = message.model_dump(exclude_none=True, by_alias=True)
        response = requests.post(self.base_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

