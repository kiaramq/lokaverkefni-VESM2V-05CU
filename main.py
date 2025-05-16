# Beacon Script

import network
import time
import uasyncio as asyncio
import random

from machine import Pin, SoftSPI
from mqtt_as import MQTTClient, config
from machine import Pin, unique_id
from neopixel import NeoPixel

from lib.dfplayer import DFPlayer
from mfrc522 import MFRC522

# ------------ Variables for script ------------
# Beacon
beacon_amount = 51
BEACON_LIST = [i for i in range(beacon_amount)]

beacon_pixel = NeoPixel(Pin(42), beacon_amount)

# RFID
sck = Pin(3) 
mosi = Pin(7)
miso = Pin(5)
rst = 4
nss = 9

# DF Speaker
df = DFPlayer(2)
df.init(tx=17, rx=16)

# Ultrasonic sensors
echo1 = Pin(10, Pin.IN)
trig1 = Pin(11, Pin.OUT)
sensor1 = [
    echo1, trig1
]

echo2 = Pin(12, Pin.IN)
trig2 = Pin(13, Pin.OUT)
sensor2 = [
    echo2, trig2
]

echo3 = Pin(37, Pin.IN)
trig3 = Pin(36, Pin.OUT)
sensor3 = [
    echo3, trig3
]

echo4 = Pin(47, Pin.IN)
trig4 = Pin(48, Pin.OUT)
sensor4 = [
    echo4, trig4
]
# All sensors
sensors = [
    sensor1,
    sensor2,
    sensor3,
    sensor4
]

# ------------ Functions for script ------------
def rangefinder(sensor):
    echo, trig = sensor
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    while not echo.value():
        pass

    start_time = time.ticks_us()

    while echo.value():
        pass

    end_time = time.ticks_us()

    total_time = time.ticks_diff(end_time, start_time)
    total_time /= 2
    speed_of_sound = 34000 / 1000000
    length = total_time * speed_of_sound


    return int(length)

# ------------ WIFI Connection -------------
# WIFI settings
config["ssid"] = "TskoliVESM"
config["wifi_pw"] = "Fallegurhestur"

# MQTT service
config["server"] = "10.201.48.77"
config["queue_len"] = 1
TOPIC_RANGEFINDER = "fjarlaegd"
TOPIC_NFC = "NFC"

client = MQTTClient(config)

# ------------ MQTT Functions -------------
async def message_receive(client):
    async for topic, message, _ in client.queue:
        message = message.decode()
        print(f"New Message: {message}")

async def message_send(client, message, topic):
    message = f"{message}".encode()
    print(f"Sending Message: {message.decode()}")
    await client.publish(TOPIC_RANGEFINDER, message)

async def subscribe_MQTT(client):
    while True:
        await client.up.wait()
        client.up.clear()
        await client.subscribe(TOPIC_MOTTAKA, 1)

# ------------ Functions -------------
def RFID_Connection():
    # Búa til og virkja SPI tenginguna
    spi = SoftSPI(baudrate=100000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)
    spi.init()

    # Búa til tilvik af RFID lesarann og tengjast honum með SPI
    rfid_lesari = MFRC522(spi=spi, gpioRst=rst, gpioCs=nss)

    (stada, korta_tegund) = rfid_lesari.request(rfid_lesari.REQIDL)
    if stada == rfid_lesari.OK: # ef eitthvað er til að lesa
        (stada, kortastrengur) = rfid_lesari.anticoll()
        if stada == rfid_lesari.OK:
            # kortanúmerið er í bytearray og því gott að 
            # breyta því í heiltölu áður en unnið er með það
            kortanumer = int.from_bytes(kortastrengur, "big")
            return kortanumer
    return None
def beacon_script():
    pass

# Beacon Program
async def main(client):
    # ---- Start Code ----
    # Londoff
    beacon_pixel.fill((0, 0, 0))
    beacon_pixel.write()
    
    # RFID Start up
    print("Waiting for RFID card!")
    while True:
        if RFID_Connection() != None:
            await df.volume(30)
            await df.play(1, 1)  # folder 1, file 1
            break
    # WiFi Start up
    print("Connecting to MQTT!")
    await client.connect()
    print("Got a connection!")
    
    # Alert steps
    alert_distance = 80
    danger_distance = 50
    
    beacon_steps = 0
    ring_len = 20 + 1
    full_break = False # Temp code maybe. Delete otherwise
    
    # Ready
    await df.wait_available()
    print("Running")
    
    while True:
        # Turn off
        if RFID_Connection() != None:
            beacon_pixel.fill((0, 0, 0))
            beacon_pixel.write()
            break
        
        # Rangefinder
        sensor_values = []
        for sensor in sensors:
            sensor_values.append(rangefinder(sensor))
        sensor_values.sort()
        min_sensor_value = sensor_values[0]
        
        # Sending Message
        print(sensor_values[0])
        await message_send(client, min_sensor_value, TOPIC_RANGEFINDER)
        
        # Step Neutral
        if min_sensor_value >= alert_distance:
            beacon_pixel.fill((0, 255, 0))
            beacon_pixel.write()
            
        elif min_sensor_value < danger_distance:
            # Play sound
            await df.volume(10)
            await df.play(1, 1)	# folder 1, file 1
            
            # Beacon LED
            for list_index in range(len(BEACON_LIST)):
                for i in range(ring_len):
                    index = (list_index + i) % len(BEACON_LIST)
                    beacon_pixel[BEACON_LIST[index]] = (255, 0, 0)
                beacon_pixel[list_index] = (0, 0, 0)
                beacon_pixel.write()
            # Clean up
            await asyncio.sleep_ms(5)
        # Step 2
        else:
            # Play sound
            await df.volume(20)
            await df.play(1, 1)  # folder 1, file 1
            
            # Beacon LED
            for list_index in range(len(BEACON_LIST)):
                for i in range(ring_len):
                    index = (list_index + i) % len(BEACON_LIST)
                    beacon_pixel[BEACON_LIST[index]] = (0, 0, 255)
                beacon_pixel[list_index] = (0, 0, 0)
                beacon_pixel.write()
            # Clean up
            await asyncio.sleep_ms(5)
try:
    asyncio.run(main(client))
finally:
    client.close()
