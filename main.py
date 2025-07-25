import RPi.GPIO as GPIO
import time
import math
import threading
from enum import Enum, auto
from collections import deque

# Constants
MIN_DUTY = 30
MAX_DUTY = 85
DUTY_STEP = 2
KICKSTART_DUTY = 100
KICKSTART_TIME = 0.01  # in seconds

class AccelerationCurve(Enum):
    LINEAR = auto()
    EASE_IN = auto()
    EASE_OUT = auto()
    EASE_IN_OUT = auto()

# Map enum values to curve functions
CURVE_FUNCTIONS = {
    AccelerationCurve.LINEAR: lambda t: t,
    AccelerationCurve.EASE_IN: lambda t: t * t,
    AccelerationCurve.EASE_OUT: lambda t: 1 - (1 - t) * (1 - t),
    AccelerationCurve.EASE_IN_OUT: lambda t: 0.5 * (1 - math.cos(math.pi * t))
}

class Motor:
    def __init__(self, in1_pin, in2_pin, en_pin, min_duty, max_duty, kickstart_duty, kickstart_time):
        self.in1 = in1_pin
        self.in2 = in2_pin
        self.en = en_pin
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
        GPIO.setup(self.en, GPIO.OUT)
        
        self.pwm = GPIO.PWM(self.en, 1000)  # 1kHz frequency
        self.pwm.start(0)
        
        # Start command processing thread
        self.worker_thread = threading.Thread(target=self._process_commands)
        self.worker_thread.start()
    
    def _process_commands(self):
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
    
    def _set_speed(self, speed):
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
            duty = min(abs(speed), self.kickstart_duty)
            self.pwm.ChangeDutyCycle(duty)
            time.sleep(self.kickstart_time)
        
        # Set actual speed
        duty = min(abs(speed), self.max_duty)
        duty = max(duty, self.min_duty) if duty > 0 else 0
        self.pwm.ChangeDutyCycle(duty)
        self.current_speed = speed
    
    def set_speed(self, speed):
        """Thread-safe method to set motor speed"""
        with self.queue_lock:
            self.command_queue.append(lambda: self._set_speed(speed))
    
    def ramp_to_speed(self, target_speed, duration=1.0, curve=AccelerationCurve.LINEAR):
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
    
    def stop(self):
        """Thread-safe method to stop the motor"""
        with self.queue_lock:
            self.command_queue.append(lambda: self._set_speed(0))
    
    def cleanup(self):
        """Clean up resources and stop background thread"""
        self.running = False
        self.worker_thread.join()
        self.pwm.stop()

if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    try:
        # Initialize motors
        motor_a = Motor(5, 6, 13, MIN_DUTY, MAX_DUTY, KICKSTART_DUTY, KICKSTART_TIME)
        motor_b = Motor(16, 26, 12, MIN_DUTY, MAX_DUTY, KICKSTART_DUTY, KICKSTART_TIME)
        
        # Test concurrent control
        print("Testing motor control")
        motor_a.set_speed(50)
        motor_b.ramp_to_speed(80, 2.0, AccelerationCurve.EASE_IN_OUT)
        time.sleep(1)
        motor_a.ramp_to_speed(-50, 1.0)
        motor_b.ramp_to_speed(-80, 2.0, AccelerationCurve.EASE_IN_OUT)
        time.sleep(3)
        motor_a.stop()
        motor_b.stop()
            
    except KeyboardInterrupt:
        print("Stopping motors...")
    
    finally:
        motor_a.cleanup()
        motor_b.cleanup()
        GPIO.cleanup()