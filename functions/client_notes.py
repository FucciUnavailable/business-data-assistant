"""
title: Client Notes
author: fucci
version: 1.0.0
required_open_webui_version: 0.3.0
"""
from typing import Optional, Dict, Any, List
import json
import os
from functions.base_function import BaseClientFunction, cache_result


def load_queries() -> Dict[str, Any]:
    """Load queries from JSON file"""
    # Get path relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    query_file = os.path.join(current_dir, 'json', 'queries.json')

    try:
        with open(query_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Warning: Query file not found at {query_file}")
        return {}
    except json.JSONDecodeError as e:
        print(f"⚠️ Warning: Invalid JSON in query file: {e}")
        return {}


# Load queries at module level (once on import)
QUERIES = load_queries()


class ClientNotesFunction(BaseClientFunction):
    """Retrieve client notes and activity history"""
    FUNCTION_NAME = "get_client_notes"
    FUNCTION_VERSION = "1.0.0"
    REQUIRED_PERMISSIONS = ["admin", "sales", "support"]

    @cache_result(ttl=300)  # Cache for 5 minutes
    def get_all_notes(
        self,
        client_id: str,
        limit: Optional[int] = 100,
        __user__: dict = {}
    ) -> str:
        """
        Get all notes for a specific client.
        :param client_id: The client identifier
        :param limit: Maximum number of notes to return (default 100)
        """
        # Validate input
        if not client_id or not client_id.strip():
            return "❌ Please provide a valid client ID."

        client_id = self._sanitize_input(client_id)

        # Check permissions (including row-level security)
        if not self._check_permissions(__user__, client_id):
            return "🔒 Access denied. You don't have permission to view this client's notes."

        # Load query from JSON
        query = QUERIES.get("client_notes", {}).get("get_all_notes")
        if not query:
            return "❌ Query configuration missing. Please check queries.json file."

        try:
            results = self._execute_query(query, (limit, client_id))

            if not results:
                return f"ℹ️ No notes found for client {client_id}."

            # Format response
            response = f"📋 **{len(results)} notes for client {client_id}:**\n\n"
            for row in results:
                created_date = row['created_date'].strftime('%Y-%m-%d %H:%M')
                response += (
                    f"**[{created_date}]** {row['action_type']}\n"
                    f"_{row['note_text']}_\n"
                    f"By: {row['created_by']} | Status: {row['status']}\n\n"
                )

            return response

        except Exception as e:
            return self._format_error_response(e)

    def execute(self, **kwargs) -> str:
        """Main entry point for OpenWebUI"""
        return self.get_all_notes(**kwargs)


# OpenWebUI requires this structure
class Tools:
    def __init__(self):
        self.notes_func = ClientNotesFunction()

    def get_all_notes(
        self,
        client_id: str,
        limit: int = 100,
        __user__: dict = {}
    ) -> str:
        """
        Get all notes for a specific client.
        :param client_id: The client identifier
        :param limit: Maximum number of notes to return (default 100)
        """
        return self.notes_func.get_all_notes(client_id, limit, __user__)
