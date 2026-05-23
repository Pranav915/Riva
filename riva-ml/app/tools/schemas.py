"""
JSON Schemas for Gemini Live Tools.
"""

TOOLS_SCHEMA = [
    {
        "function_declarations": [
            # ── Finance ──────────────────────────────────────────────
            {
                "name": "add_transaction",
                "description": (
                    "Record any financial transaction — expense, income, money lent to someone, "
                    "or money borrowed. Always pass the correct transaction_type."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "transaction_type": {
                            "type": "STRING",
                            "description": (
                                "Type of transaction: "
                                "'expense' (money spent), "
                                "'income' (money received/salary/payment), "
                                "'lended' (money lent to someone), "
                                "'borrowed' (money borrowed from someone)."
                            ),
                        },
                        "amount":      {"type": "NUMBER", "description": "Transaction amount in INR."},
                        "category":    {"type": "STRING", "description": "Category: food, transport, shopping, bills, entertainment, health, personal, salary, investment, other."},
                        "description": {"type": "STRING", "description": "Short description, e.g. 'lunch', 'Rahul borrowed ₹500', 'freelance payment'."},
                        "date":        {"type": "STRING", "description": "YYYY-MM-DD (optional, defaults to today)."},
                        "person":      {"type": "STRING", "description": "Name of person involved (only for lended/borrowed)."},
                    },
                    "required": ["transaction_type", "amount", "category"],
                },
            },
            {
                "name": "query_spending",
                "description": "Query the user's spending history and totals.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "time_range": {"type": "STRING", "description": "today | this_week | this_month | last_month | all"},
                        "category":   {"type": "STRING", "description": "Filter by category (optional)."},
                    },
                },
            },
            {
                "name": "list_expenses",
                "description": "List recent expenses so the user can pick one to edit or delete. Returns expense IDs.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "days":     {"type": "NUMBER", "description": "How many days back to look (default 7)."},
                        "category": {"type": "STRING", "description": "Filter by category (optional)."},
                        "limit":    {"type": "NUMBER", "description": "Max number to return (default 10)."},
                    },
                },
            },
            {
                "name": "update_expense",
                "description": "Update an existing expense. Call list_expenses first to get the expense_id.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "expense_id":  {"type": "STRING", "description": "MongoDB _id of the expense."},
                        "amount":      {"type": "NUMBER", "description": "New amount (optional)."},
                        "category":    {"type": "STRING", "description": "New category (optional)."},
                        "description": {"type": "STRING", "description": "New description (optional)."},
                        "date":        {"type": "STRING", "description": "New date YYYY-MM-DD (optional)."},
                    },
                    "required": ["expense_id"],
                },
            },
            {
                "name": "delete_expense",
                "description": "Permanently delete an expense. Call list_expenses first to confirm the expense_id.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "expense_id": {"type": "STRING", "description": "MongoDB _id of the expense to delete."},
                    },
                    "required": ["expense_id"],
                },
            },
            {
                "name": "get_budget_status",
                "description": "Get the user's budget limits vs current spending for this month.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "set_budget",
                "description": "Set or update the monthly budget limit for a spending category.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "category": {"type": "STRING", "description": "Category name: food, transport, shopping, bills, entertainment, health, personal, other."},
                        "limit":    {"type": "NUMBER", "description": "Monthly spending limit in INR."},
                    },
                    "required": ["category", "limit"],
                },
            },
            # ── Calendar ─────────────────────────────────────────────
            {
                "name": "schedule_event",
                "description": "Create a new event on the user's Google Calendar.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "title":       {"type": "STRING", "description": "Event title."},
                        "start_time":  {"type": "STRING", "description": "ISO 8601 start datetime."},
                        "end_time":    {"type": "STRING", "description": "ISO 8601 end datetime (optional, defaults to 1 h after start)."},
                        "description": {"type": "STRING", "description": "Event notes (optional)."},
                    },
                    "required": ["title", "start_time"],
                },
            },
            {
                "name": "update_event",
                "description": (
                    "Update an existing calendar event. "
                    "Use list_events first to get the event_id, then call this. "
                    "Only supply the fields you want to change."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "event_id":    {"type": "STRING", "description": "The Google Calendar event ID."},
                        "title":       {"type": "STRING", "description": "New title (optional)."},
                        "start_time":  {"type": "STRING", "description": "New start datetime ISO 8601 (optional)."},
                        "end_time":    {"type": "STRING", "description": "New end datetime ISO 8601 (optional)."},
                        "description": {"type": "STRING", "description": "New description (optional)."},
                    },
                    "required": ["event_id"],
                },
            },
            {
                "name": "delete_event",
                "description": "Permanently delete a calendar event. Use list_events first to confirm the event_id.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "event_id": {"type": "STRING", "description": "The Google Calendar event ID to delete."},
                    },
                    "required": ["event_id"],
                },
            },
            {
                "name": "list_events",
                "description": "List the user's upcoming calendar events.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "days": {"type": "NUMBER", "description": "How many days ahead to look (default 1)."},
                    },
                },
            },
            # ── To-Do ─────────────────────────────────────────────────
            {
                "name": "add_todo",
                "description": "Add a new task/to-do item to the user's list.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "title":    {"type": "STRING", "description": "Task title (e.g. 'Buy groceries')."},
                        "due_date": {"type": "STRING", "description": "YYYY-MM-DD (optional, defaults to today)."},
                        "due_time": {"type": "STRING", "description": "HH:MM (optional)."},
                        "priority": {"type": "STRING", "description": "high | medium | low (default: medium)."},
                        "category": {"type": "STRING", "description": "work | personal | health | study | other."},
                    },
                    "required": ["title"],
                },
            },
            {
                "name": "list_todos",
                "description": "List the user's pending to-do items.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "days":   {"type": "NUMBER", "description": "How many days ahead to look (default 1)."},
                        "status": {"type": "STRING", "description": "Filter: pending | completed (default: pending)."},
                    },
                },
            },
            {
                "name": "complete_todo",
                "description": "Mark a to-do item as completed. Use list_todos first to find the todo_id.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "todo_id": {"type": "STRING", "description": "The MongoDB ID of the todo to complete."},
                    },
                    "required": ["todo_id"],
                },
            },
            {
                "name": "delete_todo",
                "description": "Permanently delete a to-do item. Use list_todos first to confirm the todo_id.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "todo_id": {"type": "STRING", "description": "The MongoDB ID of the todo to delete."},
                    },
                    "required": ["todo_id"],
                },
            },
            {
                "name": "end_conversation",
                "description": "Call this when the user says bye, goodbye, or clearly wants to end the session.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {},
                },
            },
        ]
    }
]
