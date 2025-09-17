from pydantic import BaseModel, Field
from typing import Optional

class BaseCommand(BaseModel):
    motor: str = Field(..., pattern=r'^motor_[lr]$')
    command: str

class SetSpeedCommand(BaseCommand):
    command: str = 'set_speed'
    speed: float = Field(..., ge=-100, le=100)

class RampToSpeedCommand(BaseCommand):
    command: str = 'ramp_to_speed'
    speed: float = Field(..., ge=-100, le=100)
    duration: float = Field(1.0, gt=0)
    curve: str = Field('LINEAR', pattern=r'^(LINEAR|EASE_IN|EASE_OUT|EASE_IN_OUT)$')

class StopCommand(BaseCommand):
    command: str = 'stop'

class GetStatusCommand(BaseCommand):
    command: str = 'get_status'
