"""
Todo Service for managing user todo items.

Supports manual CRUD and items extracted from conversation by LLM.
Displayed in the sidebar for Assistant-category personas.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ...database.models import TodoItem

logger = logging.getLogger(__name__)


class TodoService:
    """Service for managing user todo items."""

    def get_todos(
        self,
        user_id: int,
        character_id: str,
        include_completed: bool = False,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Get all todos for user+character.

        Args:
            user_id: User ID
            character_id: Character ID
            include_completed: Whether to include completed todos
            db: Database session

        Returns:
            List of todo dictionaries
        """
        query = db.query(TodoItem).filter(
            and_(
                TodoItem.user_id == user_id,
                TodoItem.character_id == character_id
            )
        )

        if not include_completed:
            query = query.filter(TodoItem.is_completed == 0)

        # Order by: incomplete first, then by sort_order, then by created_at
        todos = query.order_by(
            TodoItem.is_completed,
            TodoItem.sort_order,
            TodoItem.created_at.desc()
        ).all()

        return [todo.to_dict() for todo in todos]

    def create_todo(
        self,
        user_id: int,
        character_id: str,
        text: str,
        priority: int = 2,
        due_date: Optional[datetime] = None,
        source_type: str = 'manual',
        source_message_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Create a new todo item.

        Args:
            user_id: User ID
            character_id: Character ID
            text: Todo text
            priority: Priority level (1=high, 2=medium, 3=low)
            due_date: Optional due date
            source_type: 'manual' or 'extracted'
            source_message_id: Message ID if extracted
            db: Database session

        Returns:
            Created todo dictionary
        """
        # Get max sort_order for new todo
        max_order = db.query(TodoItem.sort_order).filter(
            and_(
                TodoItem.user_id == user_id,
                TodoItem.character_id == character_id
            )
        ).order_by(TodoItem.sort_order.desc()).first()

        sort_order = (max_order[0] + 1) if max_order else 0

        todo = TodoItem(
            user_id=user_id,
            character_id=character_id,
            text=text,
            priority=priority,
            due_date=due_date,
            source_type=source_type,
            source_message_id=source_message_id,
            sort_order=sort_order
        )

        db.add(todo)
        db.commit()
        db.refresh(todo)

        logger.info(f"Created todo {todo.id} for user {user_id}, character {character_id}")
        return todo.to_dict()

    def update_todo(
        self,
        todo_id: int,
        user_id: int,
        updates: Dict[str, Any],
        db: Session = None
    ) -> Optional[Dict[str, Any]]:
        """Update a todo item.

        Args:
            todo_id: Todo ID
            user_id: User ID (for authorization)
            updates: Dictionary of fields to update
            db: Database session

        Returns:
            Updated todo dictionary, or None if not found
        """
        todo = db.query(TodoItem).filter(
            and_(
                TodoItem.id == todo_id,
                TodoItem.user_id == user_id
            )
        ).first()

        if not todo:
            return None

        # Update allowed fields
        allowed_fields = ['text', 'priority', 'due_date', 'is_completed', 'sort_order']
        for field, value in updates.items():
            if field in allowed_fields:
                if field == 'is_completed':
                    setattr(todo, field, 1 if value else 0)
                    # Set completed_at timestamp
                    if value:
                        todo.completed_at = datetime.utcnow()
                    else:
                        todo.completed_at = None
                else:
                    setattr(todo, field, value)

        db.commit()
        db.refresh(todo)

        logger.info(f"Updated todo {todo_id}")
        return todo.to_dict()

    def toggle_todo(
        self,
        todo_id: int,
        user_id: int,
        db: Session = None
    ) -> Optional[Dict[str, Any]]:
        """Toggle todo completion status.

        Args:
            todo_id: Todo ID
            user_id: User ID (for authorization)
            db: Database session

        Returns:
            Updated todo dictionary, or None if not found
        """
        todo = db.query(TodoItem).filter(
            and_(
                TodoItem.id == todo_id,
                TodoItem.user_id == user_id
            )
        ).first()

        if not todo:
            return None

        # Toggle completion
        todo.is_completed = 0 if todo.is_completed else 1
        todo.completed_at = datetime.utcnow() if todo.is_completed else None

        db.commit()
        db.refresh(todo)

        logger.info(f"Toggled todo {todo_id} to completed={bool(todo.is_completed)}")
        return todo.to_dict()

    def delete_todo(
        self,
        todo_id: int,
        user_id: int,
        db: Session = None
    ) -> bool:
        """Delete a todo item.

        Args:
            todo_id: Todo ID
            user_id: User ID (for authorization)
            db: Database session

        Returns:
            True if deleted, False if not found
        """
        todo = db.query(TodoItem).filter(
            and_(
                TodoItem.id == todo_id,
                TodoItem.user_id == user_id
            )
        ).first()

        if not todo:
            return False

        db.delete(todo)
        db.commit()

        logger.info(f"Deleted todo {todo_id}")
        return True

    def reorder_todos(
        self,
        user_id: int,
        character_id: str,
        todo_ids: List[int],
        db: Session = None
    ) -> bool:
        """Reorder todos by providing new order of IDs.

        Args:
            user_id: User ID
            character_id: Character ID
            todo_ids: List of todo IDs in new order
            db: Database session

        Returns:
            True if successful
        """
        for index, todo_id in enumerate(todo_ids):
            db.query(TodoItem).filter(
                and_(
                    TodoItem.id == todo_id,
                    TodoItem.user_id == user_id,
                    TodoItem.character_id == character_id
                )
            ).update({'sort_order': index})

        db.commit()
        logger.info(f"Reordered {len(todo_ids)} todos for user {user_id}, character {character_id}")
        return True

    def get_todo_count(
        self,
        user_id: int,
        character_id: str,
        db: Session = None
    ) -> Dict[str, int]:
        """Get count of todos (total and incomplete).

        Args:
            user_id: User ID
            character_id: Character ID
            db: Database session

        Returns:
            Dictionary with 'total' and 'incomplete' counts
        """
        total = db.query(TodoItem).filter(
            and_(
                TodoItem.user_id == user_id,
                TodoItem.character_id == character_id
            )
        ).count()

        incomplete = db.query(TodoItem).filter(
            and_(
                TodoItem.user_id == user_id,
                TodoItem.character_id == character_id,
                TodoItem.is_completed == 0
            )
        ).count()

        return {'total': total, 'incomplete': incomplete}


# Global service instance
todo_service = TodoService()
