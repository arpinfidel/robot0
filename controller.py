from typing import Any, Dict, Optional
from fastapi import WebSocket
from motor import Motor, AccelerationCurve
from models import (
    SetSpeedCommand,
    RampToSpeedCommand,
    StopCommand,
    GetStatusCommand
)

class MotorController:
    def __init__(self, motor_a: Motor, motor_b: Motor) -> None:
        self.motor_a = motor_a
        self.motor_b = motor_b
        self.command_handlers = {
            'set_speed': self.handle_set_speed,
            'ramp_to_speed': self.handle_ramp_to_speed,
            'stop': self.handle_stop,
            'get_status': self.handle_get_status
        }

    def get_motor(self, name: str) -> Optional[Motor]:
        if name == 'motor_a':
            return self.motor_a
        elif name == 'motor_b':
            return self.motor_b
        return None

    async def handle_set_speed(self, motor: Motor, cmd: SetSpeedCommand) -> None:
        motor.set_speed(cmd.speed)

    async def handle_ramp_to_speed(self, motor: Motor, cmd: RampToSpeedCommand) -> None:
        curve = AccelerationCurve[cmd.curve.upper()]
        motor.ramp_to_speed(cmd.speed, cmd.duration, curve)

    async def handle_stop(self, motor: Motor, cmd: StopCommand) -> None:
        motor.stop()

    async def handle_get_status(self, motor: Motor, cmd: GetStatusCommand) -> Dict[str, Any]:
        return {
            'speed': motor.current_speed,
            'direction': 'forward' if motor.current_speed > 0 else 'backward' if motor.current_speed < 0 else 'stopped'
        }

    async def handle_command(
        self,
        websocket: WebSocket,
        data: Dict[str, Any]
    ) -> None:
        try:
            command_type = data.get('command')
            print(command_type, data)
            match command_type:
                case 'set_speed':
                    cmd = SetSpeedCommand(**data)
                case 'ramp_to_speed':
                    cmd = RampToSpeedCommand(**data)
                case 'stop':
                    cmd = StopCommand(**data)
                case 'get_status':
                    cmd = GetStatusCommand(**data)
                case _:
                    raise ValueError(f"Unknown command: {command_type}")

            motor = self.get_motor(cmd.motor)
            if not motor:
                return

            handler = self.command_handlers.get(cmd.command)
            if handler:
                result = await handler(motor, cmd)
                if result:
                    await websocket.send_json(result)
        except Exception as e:
            await websocket.send_json({'error': str(e)})