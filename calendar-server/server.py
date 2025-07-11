import asyncio
import os
from typing import Any, Dict, List
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class MinimalCalendarServer:
    def __init__(self):
        self.server = Server("minimal-calendar-server")
        self.service = None
        self.credentials = None
        self.SCOPES = [
            'https://www.googleapis.com/auth/calendar',
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly"
        ]
        self.initialize_service()
        self.setup_tools()

    def initialize_service(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        token_path = os.path.join(script_dir, 'token.json')
        # credentials_path = os.path.join(script_dir, 'credentials.json')
        self.credentials = Credentials.from_authorized_user_file(token_path, self.SCOPES)
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def setup_tools(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="add_calendar_event",
                    description="Add a new event to Google Calendar",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Event title"},
                            "description": {"type": "string", "description": "Event description"},
                            "start_datetime": {"type": "string", "description": "Start date and time in ISO format (e.g., 2024-12-25T10:00:00)"},
                            "end_datetime": {"type": "string", "description": "End date and time in ISO format (e.g., 2024-12-25T11:00:00)"},
                            "timezone": {"type": "string", "description": "Timezone (e.g., UTC)", "default": "UTC"},
                            "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee email addresses"},
                            "location": {"type": "string", "description": "Event location"}
                        },
                        "required": ["title", "start_datetime", "end_datetime"]
                    }
                ),
                Tool(
                    name="list_calendar_events",
                    description="List upcoming calendar events",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "max_results": {"type": "integer", "description": "Maximum number of events to return", "default": 10},
                            "time_min": {"type": "string", "description": "Start time in ISO format (defaults to now)"},
                            "time_max": {"type": "string", "description": "End time in ISO format"}
                        }
                    }
                ),
                Tool(
                    name="update_calendar_event",
                    description="Update an existing Google Calendar event (title, description, start/end time only)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string", "description": "ID of the event to update"},
                            "title": {"type": "string", "description": "New event title"},
                            "description": {"type": "string", "description": "New event description"},
                            "start_datetime": {"type": "string", "description": "New start date and time in ISO format"},
                            "end_datetime": {"type": "string", "description": "New end date and time in ISO format"}
                        },
                        "required": ["event_id"]
                    }
                ),
                Tool(
                    name="delete_calendar_event",
                    description="Delete an event from Google Calendar",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string", "description": "ID of the event to delete"}
                        },
                        "required": ["event_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "add_calendar_event":
                    return await self.add_event(arguments)
                elif name == "list_calendar_events":
                    return await self.list_events(arguments)
                elif name == "update_calendar_event":
                    return await self.update_event(arguments)
                elif name == "delete_calendar_event":
                    return await self.delete_event(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def add_event(self, args: Dict[str, Any]) -> List[TextContent]:
        if not self.service:
            return [TextContent(type="text", text="Google Calendar service is not initialized. Please check authentication.")]
        title = args.get('title')
        description = args.get('description', '')
        start_datetime = args.get('start_datetime')
        end_datetime = args.get('end_datetime')
        timezone = args.get('timezone', 'UTC')
        attendees = args.get('attendees', [])
        location = args.get('location', '')
        event = {
            'summary': title,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_datetime,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': timezone,
            },
        }
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        try:
            event_result = self.service.events().insert(calendarId='primary', body=event).execute()
            return [TextContent(
                type="text",
                text=f"Event created! ID: {event_result['id']}\nEvent link: {event_result.get('htmlLink', 'N/A')}"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to create event: {str(e)}")]

    async def list_events(self, args: Dict[str, Any]) -> List[TextContent]:
        if not self.service:
            return [TextContent(type="text", text="Google Calendar service is not initialized. Please check authentication.")]
        max_results = args.get('max_results', 10)
        time_min = args.get('time_min', datetime.utcnow().isoformat() + 'Z')
        time_max = args.get('time_max')
        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            if not events:
                return [TextContent(type="text", text="No upcoming events found.")]
            event_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                event_list.append(f"- {event['summary']} ({start}) - ID: {event['id']}")
            return [TextContent(
                type="text",
                text=f"Upcoming events:\n" + '\n'.join(event_list)
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to list events: {str(e)}")]

    async def update_event(self, args: Dict[str, Any]) -> List[TextContent]:
        if not self.service:
            return [TextContent(type="text", text="Google Calendar service is not initialized. Please check authentication.")]
        event_id = args.get('event_id')
        try:
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            if 'title' in args:
                event['summary'] = args['title']
            if 'description' in args:
                event['description'] = args['description']
            if 'start_datetime' in args:
                event['start']['dateTime'] = args['start_datetime']
            if 'end_datetime' in args:
                event['end']['dateTime'] = args['end_datetime']
            updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
            return [TextContent(type="text", text=f"Event updated! ID: {updated_event['id']}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to update event: {str(e)}")]

    async def delete_event(self, args: Dict[str, Any]) -> List[TextContent]:
        if not self.service:
            return [TextContent(type="text", text="Google Calendar service is not initialized. Please check authentication.")]
        event_id = args.get('event_id')
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return [TextContent(type="text", text=f"Event {event_id} deleted!")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to delete event: {str(e)}")]

async def main():
    server = MinimalCalendarServer()
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main()) 