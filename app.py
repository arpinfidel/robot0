from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from motor import Motor
from controller import MotorController
import uvicorn
import RPi.GPIO as GPIO

# Initialize motors
motor_a = None
motor_b = None
controller = None

async def lifespan(app: FastAPI):
	# Startup
	global motor_a, motor_b, controller
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)

	# Initialize motors and controller
	motor_a = Motor(pin_a=5, pin_b=6, pin_pwm=13)
	motor_b = Motor(pin_a=16, pin_b=26, pin_pwm=12)
	controller = MotorController(motor_a, motor_b)
	yield
	# Shutdown
	if motor_a:
		motor_a.cleanup()
	if motor_b:
		motor_b.cleanup()
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