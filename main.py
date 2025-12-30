import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, get_session
from app.models import Base, Poll, PollOption, Vote
from app.redis_client import create_redis
from app.schemas import (
    PollOut,
    PollOptionOut,
    ResultsResponse,
    ResultItem,
    VoteRequest,
    VoteResponse,
)
from app.ws import ConnectionManager

manager = ConnectionManager()


def _redis_keys(poll_id: int) -> tuple[str, str]:
    return f"poll:{poll_id}:total", f"poll:{poll_id}:options"


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = create_redis()
    app.state.redis = redis

    if os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield
    await redis.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001","https://jared-undeaf-jacques.ngrok-free.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_redis(app: FastAPI) -> Redis:
    return app.state.redis


@app.get("/polls/{poll_id}", response_model=PollOut)
async def get_poll(
    poll_id: int,
    session: AsyncSession = Depends(get_session),
):
    poll = await session.get(Poll, poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    options_result = await session.execute(
        select(PollOption)
        .where(PollOption.poll_id == poll_id)
        .order_by(PollOption.sort_order, PollOption.id)
    )
    options = options_result.scalars().all()

    return PollOut(
        id=poll.id,
        title=poll.title,
        description=poll.description,
        options=[PollOptionOut(id=o.id, label=o.label) for o in options],
    )


@app.post("/polls/{poll_id}/votes", response_model=VoteResponse)
async def vote(
    poll_id: int,
    payload: VoteRequest,
    session: AsyncSession = Depends(get_session),
):
    poll = await session.get(Poll, poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    if not poll.is_active:
        raise HTTPException(status_code=400, detail="Poll is not active")

    option = await session.get(PollOption, payload.optionId)
    if not option or option.poll_id != poll_id:
        raise HTTPException(status_code=404, detail="Option not found")

    voter_token = payload.voterToken or str(uuid.uuid4())
    existing_vote_result = await session.execute(
        select(Vote).where(Vote.poll_id == poll_id, Vote.voter_token == voter_token)
    )
    existing_vote = existing_vote_result.scalar_one_or_none()

    action = "created"
    vote_id = None
    previous_option_id = None

    if existing_vote is None:
        new_vote = Vote(
            poll_id=poll_id, option_id=payload.optionId, voter_token=voter_token
        )
        session.add(new_vote)
        await session.commit()
        await session.refresh(new_vote)
        vote_id = new_vote.id
        action = "created"
    else:
        previous_option_id = existing_vote.option_id
        if existing_vote.option_id == payload.optionId:
            await session.delete(existing_vote)
            await session.commit()
            action = "canceled"
        else:
            existing_vote.option_id = payload.optionId
            await session.commit()
            vote_id = existing_vote.id
            action = "updated"

    redis: Redis = get_redis(app)
    total_key, options_key = _redis_keys(poll_id)
    cache_ready = await redis.exists(options_key, total_key) == 2
    if cache_ready:
        await _update_redis_counts(
            redis=redis,
            poll_id=poll_id,
            action=action,
            option_id=payload.optionId,
            previous_option_id=previous_option_id,
        )

    results = await _get_results(session, redis, poll_id)
    await manager.broadcast(
        poll_id,
        {
            "type": "poll_results_updated",
            "pollId": poll_id,
            "totalVotes": results.totalVotes,
            "results": [item.model_dump() for item in results.results],
        },
    )

    return VoteResponse(
        voteId=vote_id,
        pollId=poll_id,
        optionId=payload.optionId,
        voterToken=voter_token,
        action=action,
    )


@app.get("/polls/results", response_model=ResultsResponse)
async def get_results(
    session: AsyncSession = Depends(get_session),
):
    poll_result = await session.execute(
        select(Poll)
        .where(
            Poll.is_active == 1,
        )
        .order_by(Poll.id.desc())
        .limit(1)
    )
    poll = poll_result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="Active poll not found")

    redis: Redis = get_redis(app)
    return await _get_results(session, redis, poll.id)


@app.websocket("/ws/polls/{poll_id}")
async def poll_ws(websocket: WebSocket, poll_id: int):
    await manager.connect(poll_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(poll_id, websocket)


async def _update_redis_counts(
    *,
    redis: Redis,
    poll_id: int,
    action: str,
    option_id: int,
    previous_option_id: int | None,
) -> None:
    total_key, options_key = _redis_keys(poll_id)

    if action == "created":
        await redis.hincrby(options_key, str(option_id), 1)
        await redis.incr(total_key)
        return

    if action == "updated" and previous_option_id is not None:
        await redis.hincrby(options_key, str(previous_option_id), -1)
        await redis.hincrby(options_key, str(option_id), 1)
        return

    if action == "canceled" and previous_option_id is not None:
        await redis.hincrby(options_key, str(previous_option_id), -1)
        await redis.decr(total_key)


async def _get_results(
    session: AsyncSession, redis: Redis, poll_id: int
) -> ResultsResponse:
    options_result = await session.execute(
        select(PollOption)
        .where(PollOption.poll_id == poll_id)
        .order_by(PollOption.sort_order, PollOption.id)
    )
    options = options_result.scalars().all()

    total_key, options_key = _redis_keys(poll_id)
    cached_counts = await redis.hgetall(options_key)
    cached_total = await redis.get(total_key)

    if not cached_counts and cached_total is None:
        counts_result = await session.execute(
            select(Vote.option_id, func.count(Vote.id))
            .where(Vote.poll_id == poll_id)
            .group_by(Vote.option_id)
        )
        counts = {str(row[0]): int(row[1]) for row in counts_result.all()}
        total_votes = sum(counts.values())
        if counts:
            await redis.hset(options_key, mapping=counts)
        await redis.set(total_key, total_votes)
    else:
        counts = {str(k): int(v) for k, v in cached_counts.items()}
        if cached_total is None:
            total_votes = sum(counts.values())
            await redis.set(total_key, total_votes)
        else:
            total_votes = int(cached_total)

    results = [
        ResultItem(
            optionId=option.id,
            label=option.label,
            count=counts.get(str(option.id), 0),
        )
        for option in options
    ]

    return ResultsResponse(pollId=poll_id, totalVotes=total_votes, results=results)
