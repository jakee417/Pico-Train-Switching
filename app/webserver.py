"""Web server for a Raspberry Pi Pico W."""
import network
import socket
from time import sleep
from app.picozero import pico_temp_sensor, pico_led
from app.secrets import SSID, PASSWORD
import machine


def open_socket(ip: str):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    return connection

def connect() -> str:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while wlan.isconnected() == False:
        print("Waiting for connection...")
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f"Connected on {ip}")
    return ip

def webpage(temperature: int, state: str) -> str:
    #Template HTML
    html = f"""
        <!DOCTYPE html>
        <html>
        <form action="./lighton">
        <input type="submit" value="Light on" />
        </form>
        <form action="./lightoff">
        <input type="submit" value="Light off" />
        </form>
        <p>LED is {state}</p>
        <p>Temperature is {str(temperature)}</p>
        </body>
        </html>
    """
    return str(html)



def serve(connection):
    #Start a web server
    state = 'OFF'
    pico_led.off()
    while True:
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        try:
            request = request.split()[1]
        except IndexError:
            pass
        if request == '/lighton?':
            pico_led.on()
            state = 'ON'
        elif request =='/lightoff?':
            pico_led.off()
            state = 'OFF'
        temperature = pico_temp_sensor.temp
        html = webpage(temperature, state)
        client.send(html)
        client.close()

def run_webserver():
    try:
        ip = connect()
        connection = open_socket(ip)
        serve(connection)
    except KeyboardInterrupt:
        machine.reset()

run_webserver()