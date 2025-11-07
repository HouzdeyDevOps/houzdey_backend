from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.core.database import get_database
from app.api.deps import get_current_user, get_optional_current_user
from app.models.support import (
    SupportTicketCreate,
    SupportTicketUpdate,
    SupportTicket,
    FeedbackCreate,
    Feedback,
    TicketResponseCreate,
    TicketResponse,
    TicketStatus,
    TicketPriority
)
from app.models.user import User

router = APIRouter()


@router.post("/tickets", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    ticket_data: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Create a new support ticket
    """
    try:
        ticket_dict = {
            "user_id": str(current_user.id),
            "user_email": current_user.email,
            "user_name": f"{current_user.first_name} {current_user.last_name}",
            "subject": ticket_data.subject,
            "category": ticket_data.category,
            "description": ticket_data.description,
            "status": TicketStatus.OPEN,
            "priority": TicketPriority.MEDIUM,
            "attachments": ticket_data.attachments or [],
            "admin_notes": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "resolved_at": None
        }
        
        result = await db.support_tickets.insert_one(ticket_dict)
        ticket_dict["id"] = str(result.inserted_id)
        ticket_dict.pop("_id", None)
        
        return {
            "message": "Support ticket created successfully",
            "ticket": ticket_dict
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create support ticket: {str(e)}"
        )


@router.get("/tickets", response_model=List[SupportTicket])
async def get_user_tickets(
    ticket_status: Optional[TicketStatus] = None,
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get all support tickets for the current user
    """
    try:
        query = {"user_id": str(current_user.id)}
        if ticket_status:
            query["status"] = ticket_status
        
        tickets = await db.support_tickets.find(query).sort("created_at", -1).to_list(100)
        
        for ticket in tickets:
            ticket["id"] = str(ticket.pop("_id"))
        
        return tickets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tickets: {str(e)}"
        )


@router.get("/tickets/{ticket_id}", response_model=SupportTicket)
async def get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get a specific support ticket
    """
    try:
        ticket = await db.support_tickets.find_one({
            "_id": ObjectId(ticket_id),
            "user_id": str(current_user.id)
        })
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        ticket["id"] = str(ticket.pop("_id"))
        return ticket
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ticket: {str(e)}"
        )


@router.patch("/tickets/{ticket_id}", response_model=dict)
async def update_ticket(
    ticket_id: str,
    ticket_update: SupportTicketUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Update a support ticket (user can only update their own tickets)
    """
    try:
        # Check if ticket exists and belongs to user
        ticket = await db.support_tickets.find_one({
            "_id": ObjectId(ticket_id),
            "user_id": str(current_user.id)
        })
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # Prepare update data
        update_data = {k: v for k, v in ticket_update.dict(exclude_unset=True).items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        if update_data.get("status") == TicketStatus.RESOLVED:
            update_data["resolved_at"] = datetime.utcnow()
        
        # Update ticket
        await db.support_tickets.update_one(
            {"_id": ObjectId(ticket_id)},
            {"$set": update_data}
        )
        
        return {"message": "Ticket updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ticket: {str(e)}"
        )


@router.post("/tickets/{ticket_id}/responses", response_model=dict)
async def add_ticket_response(
    ticket_id: str,
    response_data: TicketResponseCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Add a response to a support ticket
    """
    try:
        # Check if ticket exists
        ticket = await db.support_tickets.find_one({"_id": ObjectId(ticket_id)})
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # Create response
        response_dict = {
            "ticket_id": ticket_id,
            "user_id": str(current_user.id),
            "user_name": f"{current_user.first_name} {current_user.last_name}",
            "user_email": current_user.email,
            "is_admin": current_user.role == "admin",
            "message": response_data.message,
            "attachments": response_data.attachments or [],
            "created_at": datetime.utcnow()
        }
        
        result = await db.ticket_responses.insert_one(response_dict)
        
        # Update ticket's updated_at
        await db.support_tickets.update_one(
            {"_id": ObjectId(ticket_id)},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
        
        return {"message": "Response added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add response: {str(e)}"
        )


@router.get("/tickets/{ticket_id}/responses", response_model=List[TicketResponse])
async def get_ticket_responses(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get all responses for a specific ticket
    """
    try:
        # Check if ticket exists and user has access
        ticket = await db.support_tickets.find_one({
            "_id": ObjectId(ticket_id),
            "user_id": str(current_user.id)
        })
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        responses = await db.ticket_responses.find(
            {"ticket_id": ticket_id}
        ).sort("created_at", 1).to_list(100)
        
        for response in responses:
            response["id"] = str(response.pop("_id"))
        
        return responses
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch responses: {str(e)}"
        )


@router.post("/feedback", response_model=dict, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback_data: FeedbackCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db=Depends(get_database)
):
    """
    Submit feedback (authenticated or anonymous)
    """
    try:
        feedback_dict = {
            "user_id": str(current_user.id) if current_user else None,
            "user_email": current_user.email if current_user else None,
            "user_name": f"{current_user.first_name} {current_user.last_name}" if current_user else "Anonymous",
            "rating": feedback_data.rating,
            "comment": feedback_data.comment,
            "page_url": feedback_data.page_url,
            "category": feedback_data.category,
            "created_at": datetime.utcnow()
        }
        
        result = await db.feedback.insert_one(feedback_dict)
        feedback_dict["id"] = str(result.inserted_id)
        feedback_dict.pop("_id", None)
        
        return {
            "message": "Thank you for your feedback!",
            "feedback": feedback_dict
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/feedback", response_model=List[Feedback])
async def get_user_feedback(
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get all feedback submitted by the current user
    """
    try:
        feedback_list = await db.feedback.find(
            {"user_id": str(current_user.id)}
        ).sort("created_at", -1).to_list(100)
        
        for feedback in feedback_list:
            feedback["id"] = str(feedback.pop("_id"))
        
        return feedback_list
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch feedback: {str(e)}"
        )


# Admin endpoints
@router.get("/admin/tickets", response_model=List[SupportTicket])
async def get_all_tickets(
    ticket_status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get all support tickets (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access all tickets"
        )
    
    try:
        query = {}
        if ticket_status:
            query["status"] = ticket_status
        if priority:
            query["priority"] = priority
        
        tickets = await db.support_tickets.find(query).sort(
            "created_at", -1
        ).skip(skip).limit(limit).to_list(limit)
        
        for ticket in tickets:
            ticket["id"] = str(ticket.pop("_id"))
        
        return tickets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tickets: {str(e)}"
        )


@router.get("/admin/feedback", response_model=List[Feedback])
async def get_all_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get all feedback (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access all feedback"
        )
    
    try:
        feedback_list = await db.feedback.find().sort(
            "created_at", -1
        ).skip(skip).limit(limit).to_list(limit)
        
        for feedback in feedback_list:
            feedback["id"] = str(feedback.pop("_id"))
        
        return feedback_list
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch feedback: {str(e)}"
        )
