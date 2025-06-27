"""
GoHighLevel Integration Manager
"""
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime
from config import settings, GHL_WORKFLOWS

logger = logging.getLogger(__name__)

class GHLManager:
    def __init__(self):
        """Initialize GHL manager"""
        self.api_key = settings.ghl_api_key
        self.location_id = settings.ghl_location_id
        self.base_url = "https://api.gohighlevel.com/v1"  # Update when you have actual endpoint
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def create_or_update_contact(self, contact_data: Dict) -> Dict:
        """Create or update contact in GHL"""
        
        # For now, return mock data since API key not provided
        if not self.api_key:
            logger.info(f"GHL Mock: Would create/update contact: {contact_data}")
            return {
                "success": True,
                "contact_id": f"mock_contact_{datetime.now().timestamp()}",
                "message": "Contact created (mock)",
                "mock": True
            }
        
        try:
            # Check if contact exists by platform ID
            search_params = {
                "locationId": self.location_id,
                "query": contact_data.get("platform_id", contact_data.get("name"))
            }
            
            # Search for existing contact
            search_response = requests.get(
                f"{self.base_url}/contacts/search",
                headers=self.headers,
                params=search_params
            )
            
            existing_contact = None
            if search_response.status_code == 200:
                contacts = search_response.json().get("contacts", [])
                if contacts:
                    existing_contact = contacts[0]
            
            # Prepare contact payload
            payload = {
                "locationId": self.location_id,
                "firstName": contact_data.get("name", "Social Media").split()[0],
                "lastName": " ".join(contact_data.get("name", "Contact").split()[1:]) or "Contact",
                "tags": contact_data.get("tags", []),
                "source": f"Social Media - {contact_data.get('platform', 'Unknown')}",
                "customFields": contact_data.get("custom_fields", {}),
                "attributions": {
                    "source": "social_media_ai",
                    "medium": contact_data.get("platform"),
                    "campaign": "social_engagement"
                }
            }
            
            if existing_contact:
                # Update existing contact
                contact_id = existing_contact["id"]
                response = requests.put(
                    f"{self.base_url}/contacts/{contact_id}",
                    headers=self.headers,
                    json=payload
                )
            else:
                # Create new contact
                response = requests.post(
                    f"{self.base_url}/contacts",
                    headers=self.headers,
                    json=payload
                )
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "contact_id": result.get("id") or existing_contact["id"],
                    "message": "Contact updated" if existing_contact else "Contact created",
                    "is_new": not bool(existing_contact)
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.error(f"GHL contact creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def trigger_workflow(self, workflow_name: str, contact_id: str, 
                        trigger_data: Dict = None) -> Dict:
        """Trigger a workflow for a contact"""
        
        # Mock response if no API key
        if not self.api_key:
            logger.info(f"GHL Mock: Would trigger workflow '{workflow_name}' for contact {contact_id}")
            return {
                "success": True,
                "message": f"Workflow '{workflow_name}' triggered (mock)",
                "mock": True
            }
        
        try:
            # Get workflow ID from mapping
            workflow_id = self._get_workflow_id(workflow_name)
            if not workflow_id:
                return {
                    "success": False,
                    "error": f"Unknown workflow: {workflow_name}"
                }
            
            payload = {
                "workflowId": workflow_id,
                "contactId": contact_id,
                "eventData": trigger_data or {}
            }
            
            response = requests.post(
                f"{self.base_url}/workflows/{workflow_id}/trigger",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Workflow '{workflow_name}' triggered successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.error(f"GHL workflow trigger failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_tags(self, contact_id: str, tags: List[str]) -> Dict:
        """Add tags to a contact"""
        
        if not self.api_key:
            logger.info(f"GHL Mock: Would add tags {tags} to contact {contact_id}")
            return {
                "success": True,
                "tags_added": tags,
                "mock": True
            }
        
        try:
            payload = {
                "tags": tags
            }
            
            response = requests.post(
                f"{self.base_url}/contacts/{contact_id}/tags",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "tags_added": tags
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.error(f"GHL tag addition failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_task(self, contact_id: str, task_data: Dict) -> Dict:
        """Create a task for a contact"""
        
        if not self.api_key:
            logger.info(f"GHL Mock: Would create task for contact {contact_id}")
            return {
                "success": True,
                "task_id": f"mock_task_{datetime.now().timestamp()}",
                "mock": True
            }
        
        try:
            payload = {
                "contactId": contact_id,
                "title": task_data.get("title", "Follow up on social media comment"),
                "description": task_data.get("description", ""),
                "dueDate": task_data.get("due_date", datetime.now().isoformat()),
                "assignedTo": task_data.get("assigned_to"),
                "status": "pending"
            }
            
            response = requests.post(
                f"{self.base_url}/tasks",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "task_id": result.get("id")
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.error(f"GHL task creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_workflow_id(self, workflow_name: str) -> Optional[str]:
        """Get workflow ID from name (would be configured in GHL)"""
        # This would typically be fetched from GHL API or configured
        # For now, return mock IDs
        workflow_map = {
            "lead_nurture_sequence": "workflow_001",
            "testimonial_request": "workflow_002",
            "support_followup": "workflow_003",
            "customer_service": "workflow_004",
            "sales_followup": "workflow_005"
        }
        return workflow_map.get(workflow_name)
    
    def test_connection(self) -> bool:
        """Test GHL API connection"""
        if not self.api_key:
            logger.warning("GHL API key not configured")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/locations/{self.location_id}",
                headers=self.headers
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"GHL connection test failed: {e}")
            return False