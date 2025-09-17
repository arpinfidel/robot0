from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from motor import Motor
from controller import MotorController
import uvicorn
import RPi.GPIO as GPIO

# Pin mapping (BCM mode)
AIN1 = 26
AIN2 = 16
BIN1 = 5
BIN2 = 6
PWMA = 13
PWMB = 12
STBY = 19

# Initialize motors
motor_l = None
motor_r = None
controller = None

async def lifespan(app: FastAPI):
	# Startup
	global motor_l, motor_r, controller
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)

	GPIO.setup(STBY, GPIO.OUT, initial=GPIO.LOW)
	GPIO.output(STBY, GPIO.HIGH)

	# Initialize motors and controller
	motor_l = Motor(pin_a=AIN1, pin_b=AIN2, pin_pwm=PWMA)
	motor_r = Motor(pin_a=BIN1, pin_b=BIN2, pin_pwm=PWMB)
	controller = MotorController(motor_l, motor_r)
	yield
	# Shutdown
	if motor_l:
		motor_l.cleanup()
	if motor_r:
		motor_r.cleanup()
	GPIO.output(STBY, GPIO.LOW)
	GPIO.cleanup()

app = FastAPI(lifespan=lifespan)
# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await controller.handle_command(websocket, data)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
