import os
import re
import httpx
import logging
from typing import Optional, Dict, Any, List
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

    async def _get_access_token(self, page_id: str, existing_token: Optional[str] = None) -> str:
        """Get page access token from Meta or reuse an existing one"""
        if existing_token:
            return existing_token
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

    def _slugify_name(self, name: str) -> str:
        slug = re.sub(r'[^a-z0-9_]', '_', name.lower())
        slug = re.sub(r'_+', '_', slug).strip('_')
        if not slug:
            slug = 'template'
        return slug[:50]

    def _prepare_body_component(self, content: str) -> Dict[str, Any]:
        placeholder_order: List[str] = []

        def replace(match: re.Match) -> str:
            key = match.group(1).strip()
            if key not in placeholder_order:
                placeholder_order.append(key)
            index = placeholder_order.index(key) + 1
            return f"{{{{{index}}}}}"

        normalized_text = re.sub(r'{([^{}]+)}', replace, content)

        example_defaults = {
            'username': 'John Doe',
            'first_name': 'John',
            'last_name': 'Doe',
            'platform': 'Instagram',
            'date': 'Jan 1, 2025',
            'time': '10:00 AM',
            'order_id': '12345',
            'code': '123456',
        }

        example_row = []
        for placeholder in placeholder_order:
            example_row.append(example_defaults.get(placeholder.lower(), 'Example value'))

        body_component: Dict[str, Any] = {
            'type': 'BODY',
            'text': normalized_text,
        }

        if example_row:
            body_component['example'] = {
                'body_text': [example_row]
            }

        return body_component

    async def submit_template(self, page_id: str, template_data: Dict[str, Any], page_access_token: Optional[str] = None) -> Dict[str, Any]:
        """Submit a template to Meta for approval"""
        try:
            # Get page access token
            access_token = await self._get_access_token(page_id, page_access_token)
            
            url = f"{self.base_url}/{page_id}/message_templates"
            
            # Convert our template format to Meta's format
            # Sanitize and validate inputs
            name = self._slugify_name(template_data['name'])
            category = template_data['category']
            content = template_data['content']
            
            # Prepare template components with placeholder mapping
            body_component = self._prepare_body_component(content)
            
            # Construct Meta template format
            meta_template = {
                'name': name,
                'category': category,
                'language': 'en_US',
                'components': [body_component]
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

    async def check_template_status(self, page_id: str, template_id: str, page_access_token: Optional[str] = None) -> Dict[str, Any]:
        """Check the status of a submitted template"""
        try:
            access_token = await self._get_access_token(page_id, page_access_token)
            
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
