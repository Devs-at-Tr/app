import os
import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class MetaTemplateAPI:
    def __init__(self):
        self.app_id = os.getenv('FACEBOOK_APP_ID')
        self.app_secret = os.getenv('FACEBOOK_APP_SECRET')
        self.api_version = 'v24.0'  # Updated to latest version
        self.base_url = f'https://graph.facebook.com/{self.api_version}'
        self.client = httpx.AsyncClient(timeout=30.0)
        
        if not self.app_id or not self.app_secret:
            logger.error("FACEBOOK_APP_ID or FACEBOOK_APP_SECRET not set in environment")

    async def _get_access_token(self, page_id: str) -> str:
        """Get page access token from Meta"""
        try:
            url = f"{self.base_url}/{page_id}"
            params = {
                'fields': 'access_token',
                'access_token': f"{self.app_id}|{self.app_secret}"
            }
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()['access_token']
        except httpx.HTTPError as e:
            logger.error(f"Failed to get Meta access token: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get Meta access token: {str(e)}")
        except KeyError as e:
            logger.error(f"Access token not found in Meta response: {str(e)}")
            raise HTTPException(status_code=500, detail="Invalid response from Meta API")

    async def submit_template(self, page_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a template to Meta for approval"""
        try:
            # Get page access token
            access_token = await self._get_access_token(page_id)
            
            url = f"{self.base_url}/{page_id}/message_templates"
            
            # Convert our template format to Meta's format
            # Sanitize and validate inputs
            name = template_data['name'][:50]  # Meta has a length limit
            category = template_data['category']
            content = template_data['content']
            
            # Prepare example text
            example_text = content.replace('{username}', 'John Doe')
            if '{platform}' in content:
                example_text = example_text.replace('{platform}', 'WhatsApp')
                
            # Construct Meta template format
            meta_template = {
                'name': name,
                'category': category,
                'language': 'en',
                'components': [
                    {
                        'type': 'BODY',
                        'text': content,
                        'example': {
                            'body_text': [example_text]
                        }
                    }
                ]
            }
            
            # Log the exact payload being sent
            logger.info(f"Meta API request - URL: {url}")
            logger.info(f"Meta API payload: {meta_template}")

            logger.info(f"Submitting template to Meta: {meta_template}")
            response = await self.client.post(
                url,
                json=meta_template,
                params={'access_token': access_token}
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Template submission successful: {result}")
            
            return {
                'id': result['id'],
                'status': result.get('status', 'PENDING'),
                'category': result.get('category', template_data['category']),
                'name': result.get('name', template_data['name'])
            }
            
        except httpx.HTTPError as e:
            error_msg = f"Meta template submission failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_data = e.response.json()
                error_msg = f"Meta API error: {error_data.get('error', {}).get('message', str(e))}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error submitting template: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    async def check_template_status(self, page_id: str, template_id: str) -> Dict[str, Any]:
        """Check the status of a submitted template"""
        try:
            access_token = await self._get_access_token(page_id)
            
            url = f"{self.base_url}/{template_id}"
            response = await self.client.get(
                url,
                params={'access_token': access_token}
            )
            response.raise_for_status()

            result = response.json()
            return {
                'id': result['id'],
                'status': result.get('status', 'UNKNOWN'),
                'category': result.get('category'),
                'name': result.get('name')
            }
            
        except httpx.HTTPError as e:
            error_msg = f"Failed to check template status: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_data = e.response.json()
                error_msg = f"Meta API error: {error_data.get('error', {}).get('message', str(e))}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error checking template status: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Create a single instance
meta_template_api = MetaTemplateAPI()