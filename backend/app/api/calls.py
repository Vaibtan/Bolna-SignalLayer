"""Call initiation API endpoints."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import DealGraphError
from app.core.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.call import (
    CallInitiateRequest,
    CallSessionOut,
    CallTimelineEventOut,
    TranscriptUtteranceOut,
)
from app.services.bolna.adapter import get_bolna_adapter
from app.services.call import service as call_svc

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["calls"])


@router.post(
    "/api/deals/{deal_id}/calls",
    response_model=CallSessionOut,
)
async def initiate_call(
    deal_id: uuid.UUID,
    payload: CallInitiateRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CallSessionOut:
    """Initiate a new outbound call for a deal stakeholder."""
    adapter = get_bolna_adapter()
    redis = get_redis_client()

    session = await call_svc.initiate_call(
        db=db,
        redis=redis,
        adapter=adapter,
        org_id=current_user.org_id,
        deal_id=deal_id,
        user_id=current_user.id,
        stakeholder_id=payload.stakeholder_id,
        objective=payload.objective,
        topics=payload.topics,
    )
    # Commit the final status (queued or failed) — the
    # initial "initiating" row was already committed by
    # the service before the external call.
    await db.commit()

    if session.status == "failed":
        raise DealGraphError(
            "Call provider could not place the call.",
            status_code=502,
        )

    call_svc.enqueue_poll(str(session.id))
    response.status_code = 201
    return CallSessionOut.model_validate(session)


@router.get(
    "/api/calls/{call_id}",
    response_model=CallSessionOut,
)
async def get_call(
    call_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CallSessionOut:
    """Fetch a call session by ID."""
    session = await call_svc.get_call_session(
        db=db,
        org_id=current_user.org_id,
        call_id=call_id,
    )
    return CallSessionOut.model_validate(session)


@router.get(
    "/api/calls/{call_id}/transcript",
    response_model=list[TranscriptUtteranceOut],
)
async def get_call_transcript(
    call_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[TranscriptUtteranceOut]:
    """Return transcript utterances for a call."""
    utterances = await call_svc.get_call_transcript(
        db=db,
        org_id=current_user.org_id,
        call_id=call_id,
    )
    return [
        TranscriptUtteranceOut.model_validate(u)
        for u in utterances
    ]


@router.get(
    "/api/calls/{call_id}/timeline",
    response_model=list[CallTimelineEventOut],
)
async def get_call_timeline(
    call_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[CallTimelineEventOut]:
    """Return call events as a timeline."""
    events = await call_svc.get_call_timeline(
        db=db,
        org_id=current_user.org_id,
        call_id=call_id,
    )
    return [
        CallTimelineEventOut.model_validate(e)
        for e in events
    ]


@router.delete(
    "/api/calls/{call_id}/transcript",
    status_code=204,
)
async def redact_transcript(
    call_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Redact (delete) transcript utterances for a call."""
    await call_svc.get_call_session(
        db=db,
        org_id=current_user.org_id,
        call_id=call_id,
    )
    await call_svc.redact_call_artifacts(db, call_id)
    logger.info(
        "audit.transcript_redacted",
        call_id=str(call_id),
        user_id=str(current_user.id),
    )
    return Response(status_code=204)
