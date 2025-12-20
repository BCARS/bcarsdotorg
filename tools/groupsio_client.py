"""
Groups.io API Client

This module provides a Python client for interacting with the Groups.io API,
specifically for managing calendar events.

API Documentation: https://groups.io/api
"""

import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv


class GroupsIOError(Exception):
    """Base exception for Groups.io API errors"""
    pass


class AuthenticationError(GroupsIOError):
    """Raised when authentication fails"""
    pass


class APIError(GroupsIOError):
    """Raised when an API request fails"""
    pass


class GroupsIOClient:
    """
    Client for interacting with the Groups.io API.
    
    Handles authentication and provides methods for managing calendar events.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the Groups.io client.
        
        Args:
            api_key: Groups.io API key (optional if set in env vars)
            base_url: API base URL (defaults to https://groups.io/api/v1)
        """
        # Load environment variables
        load_dotenv()
        
        self.api_key = api_key or os.getenv('GROUPSIO_API_KEY')
        self.base_url = base_url or os.getenv('GROUPSIO_API_URL', 'https://groups.io/api/v1')
        self.group_name = os.getenv('GROUPSIO_GROUP_ID', 'bcars')
        
        if not self.api_key:
            raise AuthenticationError(
                "No API key provided. Set GROUPSIO_API_KEY in .env file."
            )
        
        self.session = requests.Session()
        # Set up Bearer token authentication
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}'
        })
        
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the API connection by fetching activity log.
        
        Returns:
            Dict containing activity log data
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            url = f"{self.base_url}/getactivitylog"
            params = {'group_name': self.group_name, 'limit': 1}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"API connection test failed: {str(e)}")
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make an authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (without leading slash)
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            API response (dict or list)
            
        Raises:
            APIError: If the request fails
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Handle empty responses (successful deletes return empty)
            if not response.text or response.text.strip() == '':
                return {}
            
            result = response.json()
            
            # Check for error in response
            if isinstance(result, dict) and result.get('type') == 'error':
                raise APIError(f"API error: {result.get('message', 'Unknown error')}")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
                error_msg = error_data.get('message', str(e))
            except:
                error_msg = str(e)
            raise APIError(f"HTTP {e.response.status_code}: {error_msg}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
    
    def get_events(self, group_name: Optional[str] = None, 
                   start: Optional[str] = None,
                   end: Optional[str] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get calendar events for a group.
        
        Args:
            group_name: Group name (defaults to configured group)
            start: Start date filter (ISO format: YYYY-MM-DD)
            end: End date filter (ISO format: YYYY-MM-DD)
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries
        """
        group_name = group_name or self.group_name
        endpoint = "getevents"
        
        params = {
            'group_name': group_name,
            'limit': limit
        }
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        
        result = self._request('GET', endpoint, params=params)
        
        # The API returns events in a 'data' field
        if isinstance(result, dict) and 'data' in result:
            return result['data']
        return result if isinstance(result, list) else []
    
    def get_event(self, event_id: int, group_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get details for a specific event.
        
        Args:
            event_id: Event ID
            group_name: Group name (defaults to configured group)
            
        Returns:
            Event dictionary
        """
        group_name = group_name or self.group_name
        endpoint = "getevent"
        
        params = {
            'group_name': group_name,
            'event_id': event_id
        }
        
        return self._request('GET', endpoint, params=params)
    
    def add_event(self, event_data: Dict[str, Any], group_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new calendar event.
        
        Args:
            event_data: Event details (title, start_date, start_time, etc.)
            group_name: Group name (defaults to configured group)
            
        Returns:
            Created event dictionary
            
        Example event_data:
            {
                'title': 'Monthly Meeting',
                'start_date': '2025-07-03',
                'start_time': '19:30',
                'end_date': '2025-07-03',
                'end_time': '21:00',
                'location': 'Bedford American Legion',
                'description': 'Regular monthly meeting'
            }
        """
        group_name = group_name or self.group_name
        endpoint = "addevent"
        
        # Convert our user-friendly format to API format
        # The API expects ISO timestamps in start_time/end_time fields
        api_data = {'group_name': group_name}
        
        # Handle title -> name mapping
        if 'title' in event_data:
            api_data['name'] = event_data['title']
        
        # Handle date/time conversion to ISO timestamps
        if 'start_date' in event_data:
            start_date = event_data['start_date']
            start_time = event_data.get('start_time', '00:00')
            timezone_str = event_data.get('timezone', 'America/New_York')
            
            # Create ISO timestamp
            # The API expects format like: "2026-06-09T10:00:00Z" or "2026-06-09T17:00:00-07:00"
            api_data['start_time'] = f"{start_date}T{start_time}:00Z"
            
            # Handle end time
            end_date = event_data.get('end_date', start_date)
            end_time = event_data.get('end_time', start_time)
            api_data['end_time'] = f"{end_date}T{end_time}:00Z"
        elif 'start_time' in event_data and 'T' in str(event_data['start_time']):
            # Already in ISO format, pass through
            api_data['start_time'] = event_data['start_time']
            api_data['end_time'] = event_data.get('end_time', event_data['start_time'])
        
        # Copy other fields
        for field in ['location', 'description', 'timezone', 'all_day', 'rsvp', 'max_attendees']:
            if field in event_data:
                api_data[field] = event_data[field]
        
        # Use form data instead of JSON
        return self._request('POST', endpoint, data=api_data)
    
    def update_event(self, event_id: int, event_data: Dict[str, Any], 
                     group_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing calendar event.
        
        Args:
            event_id: Event ID
            event_data: Event details to update
            group_name: Group name (defaults to configured group)
            
        Returns:
            Updated event dictionary
        """
        group_name = group_name or self.group_name
        endpoint = "updateevent"
        
        # Convert to API format
        api_data = {
            'group_name': group_name,
            'event_id': event_id
        }
        
        # Handle title -> name mapping
        if 'title' in event_data:
            api_data['name'] = event_data['title']
        
        # Handle date/time conversion if provided
        if 'start_date' in event_data:
            start_date = event_data['start_date']
            start_time = event_data.get('start_time', '00:00')
            api_data['start_time'] = f"{start_date}T{start_time}:00Z"
            
            if 'end_date' in event_data or 'end_time' in event_data:
                end_date = event_data.get('end_date', start_date)
                end_time = event_data.get('end_time', start_time)
                api_data['end_time'] = f"{end_date}T{end_time}:00Z"
        
        # Copy other fields
        for field in ['location', 'description', 'timezone', 'all_day', 'rsvp', 'max_attendees']:
            if field in event_data:
                api_data[field] = event_data[field]
        
        return self._request('PATCH', endpoint, data=api_data)
    
    def delete_event(self, event_id: int, group_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a calendar event.
        
        Args:
            event_id: Event ID
            group_name: Group name (defaults to configured group)
            
        Returns:
            Deletion confirmation dictionary
        """
        group_name = group_name or self.group_name
        endpoint = "deleteevent"
        
        data = {
            'group_name': group_name,
            'event_id': event_id
        }
        
        # Note: deleteevent uses POST, not DELETE
        response = self._request('POST', endpoint, data=data)
        
        # API returns empty response on success, so return a success message
        if not response or response == '':
            return {'success': True, 'message': f'Event {event_id} deleted successfully'}
        return response
    
    def duplicate_event(self, event_id: int, new_date: str, 
                       new_time: Optional[str] = None,
                       title_suffix: Optional[str] = None,
                       group_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Duplicate an existing event to a new date.
        
        This is a convenience method that fetches an event, copies its data,
        updates the date/time, and creates a new event.
        
        Args:
            event_id: Event ID to duplicate
            new_date: New date for the duplicated event (ISO format: YYYY-MM-DD)
            new_time: New time for the duplicated event (optional, HH:MM format)
            title_suffix: Suffix to add to the event title (optional)
            group_name: Group name (defaults to configured group)
            
        Returns:
            Created event dictionary
        """
        group_name = group_name or self.group_name
        
        # Fetch the original event
        original_event = self.get_event(event_id, group_name)
        
        # Build new event data
        # Note: API returns 'name' but expects 'title', 'start_time' is ISO but we need to reconstruct
        event_data = {}
        
        # Copy basic fields with API field name mapping
        if 'name' in original_event:
            event_data['title'] = original_event['name']
            if title_suffix:
                event_data['title'] += title_suffix
        
        if 'location' in original_event:
            event_data['location'] = original_event['location']
        
        if 'description' in original_event:
            event_data['description'] = original_event['description']
        
        if 'timezone' in original_event:
            event_data['timezone'] = original_event['timezone']
        
        if 'all_day' in original_event:
            event_data['all_day'] = original_event['all_day']
        
        # Handle RSVP settings
        if 'rsvp' in original_event:
            event_data['rsvp'] = original_event['rsvp']
        if 'max_attendees' in original_event and original_event['max_attendees'] > 0:
            event_data['max_attendees'] = original_event['max_attendees']
        
        # Parse original start and end times from ISO format
        try:
            orig_start_dt = datetime.fromisoformat(original_event['start_time'].replace('Z', '+00:00'))
            orig_end_dt = datetime.fromisoformat(original_event['end_time'].replace('Z', '+00:00'))
            
            # If new_time is provided, use it; otherwise use original time
            if new_time:
                # Parse the new time
                time_parts = new_time.split(':')
                new_hour = int(time_parts[0])
                new_minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                
                # Calculate duration from original event
                duration = orig_end_dt - orig_start_dt
            else:
                # Use original time
                new_hour = orig_start_dt.hour
                new_minute = orig_start_dt.minute
                duration = orig_end_dt - orig_start_dt
            
            # Set dates and times
            event_data['start_date'] = new_date
            event_data['start_time'] = f'{new_hour:02d}:{new_minute:02d}'
            
            # Calculate end time
            new_start_dt = datetime.fromisoformat(f'{new_date}T{event_data["start_time"]}:00')
            new_end_dt = new_start_dt + duration
            
            # Check if event spans multiple days
            if new_end_dt.date() != new_start_dt.date():
                event_data['end_date'] = new_end_dt.strftime('%Y-%m-%d')
            else:
                event_data['end_date'] = new_date
            
            event_data['end_time'] = new_end_dt.strftime('%H:%M')
            
        except Exception as e:
            # Fallback: simple same-day event
            event_data['start_date'] = new_date
            event_data['end_date'] = new_date
            if new_time:
                event_data['start_time'] = new_time
                # Assume 1 hour duration
                try:
                    time_parts = new_time.split(':')
                    end_hour = (int(time_parts[0]) + 1) % 24
                    event_data['end_time'] = f'{end_hour:02d}:{time_parts[1]}'
                except:
                    event_data['end_time'] = new_time
        
        # Create the new event
        return self.add_event(event_data, group_name)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        return False

