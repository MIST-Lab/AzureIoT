#!/usr/bin/env python

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import smbus
import sys
from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue
import config as config
import pygame


from mpu6050 import mpu6050
import RPi.GPIO as GPIO
import re
from telemetry import Telemetry

# HTTP options
# Because it can poll "after 9 seconds" polls will happen effectively
# at ~10 seconds.
# Note that for scalabilty, the default value of minimumPollingTime
# is 25 minutes. For more information, see:
# https://azure.microsoft.com/documentation/articles/iot-hub-devguide/#messaging
TIMEOUT = 241000
MINIMUM_POLLING_TIME = 9

# messageTimeout - the maximum time in milliseconds until a message times out.
# The timeout period starts at IoTHubClient.send_event_async.
# By default, messages do not expire.
MESSAGE_TIMEOUT = 10000

RECEIVE_CONTEXT = 0
MESSAGE_COUNT = 0
MESSAGE_SWITCH = True
TWIN_CONTEXT = 0
SEND_REPORTED_STATE_CONTEXT = 0
METHOD_CONTEXT = 0
TEMPERATURE_ALERT = 30.0

# global counters
RECEIVE_CALLBACKS = 0
SEND_CALLBACKS = 0
BLOB_CALLBACKS = 0
TWIN_CALLBACKS = 0
SEND_REPORTED_STATE_CALLBACKS = 0
METHOD_CALLBACKS = 0
EVENT_SUCCESS = "success"
EVENT_FAILED = "failed"

# chose HTTP, AMQP or MQTT as transport protocol
PROTOCOL = IoTHubTransportProvider.MQTT

# String containing Hostname, Device Id & Device Key in the format:
# "HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>"
telemetry = Telemetry()

if len(sys.argv) < 2:
    # print ( "You need to provide the device connection string as command line arguments." )
    telemetry.send_telemetry_data(None, EVENT_FAILED, "Device connection string is not provided")
    sys.exit(0)

def is_correct_connection_string():
    m = re.search("HostName=.*;DeviceId=.*;", CONNECTION_STRING)
    if m:
        return True
    else:
        return False

CONNECTION_STRING = sys.argv[1]

if not is_correct_connection_string():
    # print ( "Device connection string is not correct." )
    telemetry.send_telemetry_data(None, EVENT_FAILED, "Device connection string is not correct.")
    sys.exit(0)

MSG_TXT = "{\"deviceId\": \"Raspberry Pi - Python\",\"temperature\": %f,\"all data\": %s}"

GPIO.setmode(GPIO.BOARD)
GPIO.setup(config.GPIO_PIN_ADDRESS, GPIO.OUT)
GPIO.output(config.GPIO_PIN_ADDRESS, GPIO.HIGH)

def receive_message_callback(message, counter):
    global RECEIVE_CALLBACKS
    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    # print ( "Received Message [%d]:" % counter )
    # print ( "    Data: <<<%s>>> & Size=%d" % (message_buffer[:size].decode("utf-8"), size) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    # print ( "    Properties: %s" % key_value_pair )
    counter += 1
    RECEIVE_CALLBACKS += 1
    # print ( "    Total calls received: %d" % RECEIVE_CALLBACKS )
    return IoTHubMessageDispositionResult.ACCEPTED


def send_confirmation_callback(message, result, user_context):
    global SEND_CALLBACKS
    # print ( "Confirmation[%d] received for message with result = %s" % (user_context, result) )
    map_properties = message.properties()
    # print ( "    message_id: %s" % message.message_id )
    # print ( "    correlation_id: %s" % message.correlation_id )
    key_value_pair = map_properties.get_internals()
    # print ( "    Properties: %s" % key_value_pair )
    SEND_CALLBACKS += 1
    # print ( "    Total calls confirmed: %d" % SEND_CALLBACKS )
    #led_blink()


def device_twin_callback(update_state, payload, user_context):
    global TWIN_CALLBACKS
    # print ( "\nTwin callback called with:\nupdateStatus = %s\npayload = %s\ncontext = %s" % (update_state, payload, user_context) )
    TWIN_CALLBACKS += 1
    # print ( "Total calls confirmed: %d\n" % TWIN_CALLBACKS )


def send_reported_state_callback(status_code, user_context):
    global SEND_REPORTED_STATE_CALLBACKS
    # print ( "Confirmation for reported state received with:\nstatus_code = [%d]\ncontext = %s" % (status_code, user_context) )
    SEND_REPORTED_STATE_CALLBACKS += 1
    # print ( "    Total calls confirmed: %d" % SEND_REPORTED_STATE_CALLBACKS )


def device_method_callback(method_name, payload, user_context):
    global METHOD_CALLBACKS,MESSAGE_SWITCH
    # print ( "\nMethod callback called with:\nmethodName = %s\npayload = %s\ncontext = %s" % (method_name, payload, user_context) )
    METHOD_CALLBACKS += 1
    # print ( "Total calls confirmed: %d\n" % METHOD_CALLBACKS )
    device_method_return_value = DeviceMethodReturnValue()
    device_method_return_value.response = "{ \"Response\": \"This is the response from the device\" }"
    device_method_return_value.status = 200
    if method_name == "start":
        MESSAGE_SWITCH = True
        # print ( "Start sending message\n" )
        device_method_return_value.response = "{ \"Response\": \"Successfully started\" }"
        return device_method_return_value
    if method_name == "stop":
        MESSAGE_SWITCH = False
        # print ( "Stop sending message\n" )
        device_method_return_value.response = "{ \"Response\": \"Successfully stopped\" }"
        return device_method_return_value
    return device_method_return_value


def blob_upload_conf_callback(result, user_context):
    global BLOB_CALLBACKS
    # print ( "Blob upload confirmation[%d] received for message with result = %s" % (user_context, result) )
    BLOB_CALLBACKS += 1
    # print ( "    Total calls confirmed: %d" % BLOB_CALLBACKS )


def iothub_client_init():
    # prepare iothub client
    client = IoTHubClient(CONNECTION_STRING, PROTOCOL)
    client.set_option("product_info", "HappyPath_RaspberryPi-Python")
    if client.protocol == IoTHubTransportProvider.HTTP:
        client.set_option("timeout", TIMEOUT)
        client.set_option("MinimumPollingTime", MINIMUM_POLLING_TIME)
    # set the time until a message times out
    client.set_option("messageTimeout", MESSAGE_TIMEOUT)
    # to enable MQTT logging set to 1
    if client.protocol == IoTHubTransportProvider.MQTT:
        client.set_option("logtrace", 0)
    client.set_message_callback(
        receive_message_callback, RECEIVE_CONTEXT)
    if client.protocol == IoTHubTransportProvider.MQTT or client.protocol == IoTHubTransportProvider.MQTT_WS:
        client.set_device_twin_callback(
            device_twin_callback, TWIN_CONTEXT)
        client.set_device_method_callback(
            device_method_callback, METHOD_CONTEXT)
    return client


def print_last_message_time(client):
    try:
        last_message = client.get_last_message_receive_time()
        # print ( "Last Message: %s" % time.asctime(time.localtime(last_message)) )
        # print ( "Actual time : %s" % time.asctime() )
    except IoTHubClientError as iothub_client_error:
        if iothub_client_error.args[0].result == IoTHubClientResult.INDEFINITE_TIME:
            print ( "No message received" )
        else:
            print ( iothub_client_error )

def sound_play():
    pygame.init()
    pygame.mixer.init(44100)
    pygame.mixer.music.load('youDare.mp3')
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        led_blink()
        pygame.event.wait()
    

def led_blink():
    for index in range(1,20):
        GPIO.output(config.GPIO_PIN_ADDRESS, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(config.GPIO_PIN_ADDRESS, GPIO.LOW)
        time.sleep(0.5)

def usage():
    print ( "Usage: iothub_client_sample.py -p <protocol> -c <connectionstring>" )
    # print ( "    protocol        : <amqp, amqp_ws, http, mqtt, mqtt_ws>" )
    # print ( "    connectionstring: <HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>>" )

def parse_iot_hub_name():
    m = re.search("HostName=(.*?)\.", CONNECTION_STRING)
    return m.group(1)

BUS = smbus.SMBus(1)

def write_word(addr, data):
	global BLEN
	temp = data
	if BLEN == 1:
		temp |= 0x08
	else:
		temp &= 0xF7
	BUS.write_byte(addr ,temp)

def send_command(comm):
	# Send bit7-4 firstly
	buf = comm & 0xF0
	buf |= 0x04               # RS = 0, RW = 0, EN = 1
	write_word(LCD_ADDR ,buf)
	time.sleep(0.002)
	buf &= 0xFB               # Make EN = 0
	write_word(LCD_ADDR ,buf)

	# Send bit3-0 secondly
	buf = (comm & 0x0F) << 4
	buf |= 0x04               # RS = 0, RW = 0, EN = 1
	write_word(LCD_ADDR ,buf)
	time.sleep(0.002)
	buf &= 0xFB               # Make EN = 0
	write_word(LCD_ADDR ,buf)

def send_data(data):
	# Send bit7-4 firstly
	buf = data & 0xF0
	buf |= 0x05               # RS = 1, RW = 0, EN = 1
	write_word(LCD_ADDR ,buf)
	time.sleep(0.002)
	buf &= 0xFB               # Make EN = 0
	write_word(LCD_ADDR ,buf)

	# Send bit3-0 secondly
	buf = (data & 0x0F) << 4
	buf |= 0x05               # RS = 1, RW = 0, EN = 1
	write_word(LCD_ADDR ,buf)
	time.sleep(0.002)
	buf &= 0xFB               # Make EN = 0
	write_word(LCD_ADDR ,buf)

def init(addr, bl):
#	global BUS
#	BUS = smbus.SMBus(1)
	global LCD_ADDR
	global BLEN
	LCD_ADDR = addr
	BLEN = bl
	try:
		send_command(0x33) # Must initialize to 8-line mode at first
		time.sleep(0.005)
		send_command(0x32) # Then initialize to 4-line mode
		time.sleep(0.005)
		send_command(0x28) # 2 Lines & 5*7 dots
		time.sleep(0.005)
		send_command(0x0C) # Enable display without cursor
		time.sleep(0.005)
		send_command(0x01) # Clear Screen
		BUS.write_byte(LCD_ADDR, 0x08)
	except:
		return False
	else:
		return True

def clear():
	send_command(0x01) # Clear Screen

def openlight():  # Enable the backlight
	BUS.write_byte(0x27,0x08)
	BUS.close()

def write(x, y, str):
	if x < 0:
		x = 0
	if x > 15:
		x = 15
	if y <0:
		y = 0
	if y > 1:
		y = 1

	# Move cursor
	addr = 0x80 + 0x40 * y + x
	send_command(addr)

	for chr in str:
		send_data(ord(chr))


def lcd_show():
    init(0x27, 1)
    write(4, 0, 'YOU DARE')
    write(1, 1, 'ENTER MY LAND')


def iothub_client_sample_run():
    try:
        client = iothub_client_init()

        if client.protocol == IoTHubTransportProvider.MQTT:
            # print ( "IoTHubClient is reporting state" )
            reported_state = "{\"newState\":\"standBy\"}"
            client.send_reported_state(reported_state, len(reported_state), send_reported_state_callback, SEND_REPORTED_STATE_CONTEXT)
    
        sensor = mpu6050(address = config.I2C_ADDRESS)

        telemetry.send_telemetry_data(parse_iot_hub_name(), EVENT_SUCCESS, "IoT hub connection is established")

        while True:
            global MESSAGE_COUNT,MESSAGE_SWITCH
            if MESSAGE_SWITCH:
                # if (MESSAGE_COUNT % 5 == 0):
                    # lcd_show()
                    # led_blink()
                    # sound_play()
                
                # send a few messages every minute
                # # print ( "IoTHubClient sending %d messages" % MESSAGE_COUNT )

                all_data = sensor.get_accel_data(g=True)
                all_dataII = sensor.get_all_data()
                temperature = sensor.get_temp()
                msg_txt_formatted = MSG_TXT % (
                    temperature,
                    all_data)
                limitTagY = all_data['y']
                limitTagZ = all_data['z']
                print(all_data)
                # print (limitTagY)
                # print (limitTagZ)
                limitTag = 0.20
                tagA = limitTagY*limitTagY
                tagB = limitTagZ*limitTagZ
                if (tagA + tagB > limitTag):
                    print ("ERROR")
                    print (all_data)
                # if (MESSAGE_COUNT % 2 == 0):
                #     print(MESSAGE_COUNT)
                # if (MESSAGE_COUNT % 7 == 0  and MESSAGE_COUNT > 0):
                #     print ("ERROR")
                #     lcd_show()
                #     sound_play()
                # print (msg_txt_formatted)
                message = IoTHubMessage(msg_txt_formatted)
                # optional: assign ids
                message.message_id = "message_%d" % MESSAGE_COUNT
                message.correlation_id = "correlation_%d" % MESSAGE_COUNT
                # optional: assign properties
                prop_map = message.properties()
                prop_map.add("temperatureAlert", "true" if temperature > TEMPERATURE_ALERT else "false")

                client.send_event_async(message, send_confirmation_callback, MESSAGE_COUNT)
                # # print ( "IoTHubClient.send_event_async accepted message [%d] for transmission to IoT Hub." % MESSAGE_COUNT )

                status = client.get_send_status()
                # # print ( "Send status: %s" % status )
                MESSAGE_COUNT += 1
            time.sleep(config.MESSAGE_TIMESPAN / 1000.0)

    except IoTHubError as iothub_error:
        # print ( "Unexpected error %s from IoTHub" % iothub_error )
        telemetry.send_telemetry_data(parse_iot_hub_name(), EVENT_FAILED, "Unexpected error %s from IoTHub" % iothub_error)
        return
    except KeyboardInterrupt:
        print ( "IoTHubClient sample stopped" )

    # print_last_message_time(client)

if __name__ == "__main__":
    print ( "\nPython %s" % sys.version )
    # print ( "IoT Hub Client for Python" )

    iothub_client_sample_run()
