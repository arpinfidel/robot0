from enum import Enum, auto
import math
import time
import threading
import RPi.GPIO as GPIO
from collections import deque
from typing import Callable, Dict

# Constants
MIN_DUTY = 30
MAX_DUTY = 100
DUTY_STEP = 2
KICKSTART_DUTY = 65
KICKSTART_TIME = 0.01  # in seconds
FREQ = 1000  # PWM frequency in Hz

class AccelerationCurve(Enum):
    LINEAR = auto()
    EASE_IN = auto()
    EASE_OUT = auto()
    EASE_IN_OUT = auto()

# Map enum values to curve functions
CURVE_FUNCTIONS: Dict[AccelerationCurve, Callable[[float], float]] = {
    AccelerationCurve.LINEAR: lambda t: t,
    AccelerationCurve.EASE_IN: lambda t: t * t,
    AccelerationCurve.EASE_OUT: lambda t: 1 - (1 - t) * (1 - t),
    AccelerationCurve.EASE_IN_OUT: lambda t: 0.5 * (1 - math.cos(math.pi * t))
}

class Motor:
    def __init__(
        self,
        pin_a: int,
        pin_b: int,
        pin_pwm: int,
        min_duty: int = MIN_DUTY,
        max_duty: int = MAX_DUTY,
        kickstart_duty: int = KICKSTART_DUTY,
        kickstart_time: float = KICKSTART_TIME,
    ) -> None:
        self.in1 = pin_a
        self.in2 = pin_b
        self.pwm = pin_pwm
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.kickstart_duty = kickstart_duty
        self.kickstart_time = kickstart_time
        self.current_speed = 0

        # Thread-safe command queue
        self.command_queue = deque()
        self.queue_lock = threading.Lock()
        self.running = True
        
        GPIO.setup(self.in1, GPIO.OUT)
        GPIO.setup(self.in2, GPIO.OUT)
        GPIO.setup(self.pwm, GPIO.OUT)

        self.pwm = GPIO.PWM(self.pwm, FREQ)
        self.pwm.start(0)

        # Start command processing thread
        self.worker_thread = threading.Thread(target=self._process_commands)
        self.worker_thread.start()

    def _process_commands(self) -> None:
        """Background thread that processes commands from queue"""
        while self.running:
            with self.queue_lock:
                if self.command_queue:
                    cmd = self.command_queue.popleft()
                else:
                    cmd = None

            if cmd:
                cmd()
            else:
                time.sleep(0.01)  # Small sleep to prevent busy waiting

    def _set_speed(self, speed: float) -> None:
        """Internal method to set motor speed (-100 to 100)"""
        # Handle direction
        if speed > 0:
            GPIO.output(self.in1, GPIO.HIGH)
            GPIO.output(self.in2, GPIO.LOW)
        elif speed < 0:
            GPIO.output(self.in1, GPIO.LOW)
            GPIO.output(self.in2, GPIO.HIGH)
        else:  # speed == 0
            GPIO.output(self.in1, GPIO.LOW)
            GPIO.output(self.in2, GPIO.LOW)

        # Handle kickstart if going from 0 to non-zero
        if self.current_speed == 0 and speed != 0:
            duty = self.kickstart_duty
            self.pwm.ChangeDutyCycle(duty)
            time.sleep(self.kickstart_time)

        # Set actual speed
        duty = min(abs(speed), self.max_duty)
        duty = max(duty, self.min_duty) if duty > 0 else 0
        self.pwm.ChangeDutyCycle(duty)
        self.current_speed = speed

    def set_speed(self, speed: float) -> None:
        """Thread-safe method to set motor speed"""
        with self.queue_lock:
            self.command_queue.append(lambda: self._set_speed(speed))

    def ramp_to_speed(
        self,
        target_speed: float,
        duration: float = 1.0,
        curve: AccelerationCurve = AccelerationCurve.LINEAR
    ) -> None:
        """Thread-safe method to gradually change speed"""
        def ramp_task():
            start_speed = self.current_speed
            steps = int(duration * 100)  # 100 steps per second
            step_time = duration / steps

            for i in range(1, steps + 1):
                t = i / steps  # Normalized time (0 to 1)
                progress = CURVE_FUNCTIONS[curve](t)
                current_speed = start_speed + (target_speed - start_speed) * progress
                self._set_speed(current_speed)
                time.sleep(step_time)

        with self.queue_lock:
            self.command_queue.append(ramp_task)

    def stop(self) -> None:
        """Thread-safe method to stop the motor"""
        with self.queue_lock:
            self.command_queue.append(lambda: self._set_speed(0))

    def cleanup(self) -> None:
        """Clean up resources and stop background thread"""
        self.running = False
        self.worker_thread.join()
        self.pwm.stop()
