"""
Todo API routes for MinouChat.

Provides endpoints for managing user todo items in the sidebar.
"""

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.todo_service import todo_service
from ..core.clerk_auth import get_current_user_from_session
from ...database.config import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/todos", tags=["todos"])


# Request/Response models
class TodoCreateRequest(BaseModel):
    character_id: str
    text: str
    priority: int = 2  # 1=high, 2=medium, 3=low
    due_date: Optional[str] = None


class TodoUpdateRequest(BaseModel):
    text: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[str] = None
    is_completed: Optional[bool] = None


class TodoReorderRequest(BaseModel):
    character_id: str
    todo_ids: List[int]


@router.get("")
async def list_todos(
    request: Request,
    character_id: str = Query(..., description="Character ID"),
    include_completed: bool = Query(False, description="Include completed todos"),
    db: Session = Depends(get_db)
):
    """List todos for a specific character.

    Args:
        character_id: Character ID to filter by
        include_completed: Whether to include completed todos

    Returns:
        List of todos
    """
    try:
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        todos = todo_service.get_todos(
            user_id=current_user.id,
            character_id=character_id,
            include_completed=include_completed,
            db=db
        )

        counts = todo_service.get_todo_count(
            user_id=current_user.id,
            character_id=character_id,
            db=db
        )

        return {
            "todos": todos,
            "total": counts['total'],
            "incomplete": counts['incomplete']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing todos: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list todos")


@router.post("")
async def create_todo(
    request: Request,
    todo_data: TodoCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new todo item.

    Args:
        todo_data: Todo creation data

    Returns:
        Created todo
    """
    try:
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Parse due_date if provided
        due_date = None
        if todo_data.due_date:
            try:
                due_date = datetime.fromisoformat(todo_data.due_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid due_date format")

        todo = todo_service.create_todo(
            user_id=current_user.id,
            character_id=todo_data.character_id,
            text=todo_data.text,
            priority=todo_data.priority,
            due_date=due_date,
            source_type='manual',
            db=db
        )

        return todo

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating todo: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create todo")


@router.put("/{todo_id}")
async def update_todo(
    todo_id: int,
    request: Request,
    todo_data: TodoUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update a todo item.

    Args:
        todo_id: Todo ID
        todo_data: Fields to update

    Returns:
        Updated todo
    """
    try:
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        updates = {}
        if todo_data.text is not None:
            updates['text'] = todo_data.text
        if todo_data.priority is not None:
            updates['priority'] = todo_data.priority
        if todo_data.is_completed is not None:
            updates['is_completed'] = todo_data.is_completed
        if todo_data.due_date is not None:
            try:
                updates['due_date'] = datetime.fromisoformat(
                    todo_data.due_date.replace('Z', '+00:00')
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid due_date format")

        todo = todo_service.update_todo(
            todo_id=todo_id,
            user_id=current_user.id,
            updates=updates,
            db=db
        )

        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")

        return todo

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating todo {todo_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update todo")


@router.put("/{todo_id}/toggle")
async def toggle_todo(
    todo_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Toggle todo completion status.

    Args:
        todo_id: Todo ID

    Returns:
        Updated todo
    """
    try:
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        todo = todo_service.toggle_todo(
            todo_id=todo_id,
            user_id=current_user.id,
            db=db
        )

        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")

        return todo

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling todo {todo_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to toggle todo")


@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a todo item.

    Args:
        todo_id: Todo ID

    Returns:
        Success message
    """
    try:
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        deleted = todo_service.delete_todo(
            todo_id=todo_id,
            user_id=current_user.id,
            db=db
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Todo not found")

        return {"message": "Todo deleted", "id": todo_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting todo {todo_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete todo")


@router.put("/reorder")
async def reorder_todos(
    request: Request,
    reorder_data: TodoReorderRequest,
    db: Session = Depends(get_db)
):
    """Reorder todos by providing new order of IDs.

    Args:
        reorder_data: Character ID and list of todo IDs in new order

    Returns:
        Success message
    """
    try:
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        todo_service.reorder_todos(
            user_id=current_user.id,
            character_id=reorder_data.character_id,
            todo_ids=reorder_data.todo_ids,
            db=db
        )

        return {"message": "Todos reordered", "count": len(reorder_data.todo_ids)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering todos: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reorder todos")
