from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, INTEGER, SMALLINT, TEXT, VARCHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    title: Mapped[str] = mapped_column(VARCHAR(200))
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    is_active: Mapped[int] = mapped_column(SMALLINT, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DATETIME, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    options: Mapped[list["PollOption"]] = relationship(
        back_populates="poll", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_polls_active", "is_active"),
    )


class PollOption(Base):
    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    poll_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("polls.id", ondelete="CASCADE")
    )
    label: Mapped[str] = mapped_column(VARCHAR(200))
    sort_order: Mapped[int] = mapped_column(INTEGER, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DATETIME, server_default=func.current_timestamp()
    )

    poll: Mapped["Poll"] = relationship(back_populates="options")

    __table_args__ = (
        Index("idx_poll_options_poll", "poll_id", "sort_order"),
    )


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    poll_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("polls.id", ondelete="CASCADE")
    )
    option_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("poll_options.id", ondelete="CASCADE")
    )
    voter_token: Mapped[str] = mapped_column(VARCHAR(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DATETIME, server_default=func.current_timestamp()
    )

    __table_args__ = (
        UniqueConstraint("poll_id", "voter_token", name="uniq_vote_per_poll"),
        Index("idx_votes_poll", "poll_id"),
        Index("idx_votes_option", "option_id"),
    )
