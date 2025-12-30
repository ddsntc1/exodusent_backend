from typing import Literal

from pydantic import BaseModel


class PollOptionOut(BaseModel):
    id: int
    label: str


class PollOut(BaseModel):
    id: int
    title: str
    description: str | None
    options: list[PollOptionOut]


class VoteRequest(BaseModel):
    optionId: int
    voterToken: str | None = None


class VoteResponse(BaseModel):
    voteId: int | None
    pollId: int
    optionId: int
    voterToken: str
    action: Literal["created", "updated", "canceled"]


class ResultItem(BaseModel):
    optionId: int
    label: str
    count: int


class ResultsResponse(BaseModel):
    pollId: int
    totalVotes: int
    results: list[ResultItem]
