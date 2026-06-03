from datetime import date, datetime
from uuid import UUID

from nam_db.enums import Strategy
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


def _validate_minimum_age(value: date) -> date:
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 18:
        msg = "User must be at least 18 years old"
        raise ValueError(msg)
    return value


class UserCreate(BaseModel):
    firstname: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    strategy: Strategy
    goals: str = Field(min_length=1)

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, value: date) -> date:
        return _validate_minimum_age(value)


class UserUpdate(BaseModel):
    firstname: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    strategy: Strategy | None = None
    goals: str | None = Field(default=None, min_length=1)

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, value: date | None) -> date | None:
        if value is None:
            return value
        return _validate_minimum_age(value)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UserUpdate":
        if not any(
            value is not None
            for value in (self.firstname, self.date_of_birth, self.strategy, self.goals)
        ):
            msg = "At least one field must be provided for update"
            raise ValueError(msg)
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    firstname: str
    date_of_birth: date
    strategy: Strategy
    goals: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
