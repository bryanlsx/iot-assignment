# Grovepi libraries ------------------------------------
from datetime import datetime
from grovepi import *
from queue import Queue
import threading
from grove_rgb_lcd import *
import uuid
import json
import time
# RFID libraries
import serial
# Database libraries
from google.cloud import firestore
from google.oauth2 import service_account
# ------------------------------------------------------


# RFID ------------------------------------------------------------
rpiser1 = serial.Serial('/dev/ttyS0',
                       baudrate=9600, timeout=1,
                       bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                       xonxoff=False, rtscts=False, dsrdtr=False) #RPISER port
rpiser1.flushInput()
rpiser1.flushOutput()
# -----------------------------------------------------------------

# Device Information -----------------------------------
mac_address = uuid.getnode()
mac_address_hex = ':'.join(['{:02x}'.format((mac_address >> elements) & 0xff) for elements in range(0,8*6,8)][::-1])
# ------------------------------------------------------


# Connect to Firestore database ------------------------
# Connect to firestore database by using JSON account key
db = firestore.Client.from_service_account_json("firestore-key.json")

# Lists out all the collection in the database (For user verification purposes)
userList = [collection.id for collection in db.collections()]


# ------------------------------------------------------

# List of sensors ===================================
dhtSensor = 7          # D7
lightSensor = 15       # A1
moistureSensor = 16    # A2
water_sensor = 2       # D2
led_threshold = 5      # D5
led_actuators = 6      # D6
relayForPump = 14      # A0
relayForLight = 4      # D4


pinMode(lightSensor, "INPUT")
pinMode(dhtSensor, "INPUT")
pinMode(moistureSensor, "INPUT")
pinMode(water_sensor,"INPUT")
pinMode(led_threshold, "OUTPUT")
pinMode(led_actuators, "OUTPUT")
pinMode(relayForPump, "OUTPUT")
pinMode(relayForLight, "OUTPUT")
# ------------------------------------------------------



    
# tempHum Function --------------   
def tempHum(temp, hum, moist, light, username):
    # get threshold from firestore
    threshold_dict = threshold_read(username)
    temp_threshold = threshold_dict['temperature']
    hum_threshold = threshold_dict['humidity']


    if ((temp >= temp_threshold) and (hum <= hum_threshold)):
        print("Air become drier")
        #To alert user that the threshold has been hit for the plant
        digitalWrite(led_threshold, 1)

        #Run soilMoisture Module
        soilMoist(moist, username)

    else:
        print("Air become wet")
        #Off lights, haven't cross threshold
        digitalWrite(led_threshold, 0)

        #Run lightIntensity Module
        high = lightIntensity(light, username)
        
        

# soilMoist Function --------------    
def soilMoist(moisture, username):
    # get threshold from firestore
    threshold_dict = threshold_read(username)
    moisture_threshold = threshold_dict['moisture']
    
    if moisture < moisture_threshold:
        print("Low moisture")
        #Tell user that there's low moisture level in soil
        digitalWrite(led_threshold, 1)
        waterLevel()
    else:
        print("Enough moisture")
        digitalWrite(led_threshold, 0)
    
        


# lightIntensity Function -------------- 
def lightIntensity(light, username):

    # get threshold from firestore
    threshold_dict = threshold_read(username)
    light_threshold = threshold_dict['light']


    # check if light exceed threshold value
    # yes > turn on relay(light shade), no > turn on led(light bulb)
    if light >= light_threshold:
        print("High Light Intensity Detected!!")
        # light bulb off, light shade on
        digitalWrite(led_actuators, 0)
        digitalWrite(relayForLight,1)
    else:
        print("Low Light Intensity Detected!!")
        # light bulb on, light shade off
        digitalWrite(led_actuators, 1)
        digitalWrite(relayForLight,0)

    


# waterLevel Function --------------         
def waterLevel():
    waterlvl = digitalRead(water_sensor)

    # if water level < 10, turn off relay(water pump) & light up led
    # waterSensor, 0 = got water, 1 = no water
    if (waterlvl == 1):
        print("low water level, please refill water")
        # led on signifies that the water is insufficient
        digitalWrite(led_threshold, 1)
        digitalWrite(relay,0)
    else:
        #show that enough water to run pump
        digitalWrite(led_threshold, 0)
        #open relay for water pump
        digitalWrite(relay,1)
    time.sleep(1)



# read threshold from database function ----------------
def threshold_read(username):
    return db.collection(username).document(mac_address_hex).get().to_dict()


# Main System to run Function?? --------------     
# Might be replaced by sensor reading loop? --------------      
def mainSys(username):
    cont = True
    while cont:
        # Get current datetime
        now = datetime.now()
        curr = now.strftime("%d-%m-%Y %H:%M:%S")

        # read rfid value
        register_iden = str(rpiser1.read(14))

         # read value(temp,humidty) from dhtsensor
        [temp, hum] = dht(dhtSensor, 0)
        light = analogRead(lightSensor)
        moist = analogRead(moistureSensor)
        print("Temp = %.2f, hum = %.2f, light = %d, moisture = %d" %(temp, hum, light, moist))
        
        # convert to string
        t = str(temp)
        h = str(hum)
        l = str(light)
        m = str(moist)
        
        #print on the LCD screen for real time display
        setRGB(0, 255, 0)
        setText("T=" + t + "\337" + "C   H=" +  h + "%" + "L=" + l + "  M=" + m)
        

        # Store sensor values into database
        db.collection(username).document(mac_address_hex).collection(curr).set({
            'humidity': h,
            'lightIntensity': l,
            'moisture': m,
            'temperature': t
        })

        if str(register_iden) != "b''":
            print(register_iden)

            # Store rfid value into database
            db.collection('currentUser').collection('curr').update({'rfid': register_iden})
            time.sleep(10)
            
            #Clear secret
            register_iden = "b''"
            print(register_iden)
        

        # call temperature and humidity module
        tempHum(temp, hum, moist, light, username)
        time.sleep(60)
        # ============================================
# -----------------------------------------------------


# Main program ----------------------------------------------------------------------------
if __name__ == "__main__":
    
    username = input("Enter your registered username : ")

    if len(username) == 0:
        print("Username should not be EMPTY!")

    elif username not in userList:
        print("Username has not been registered")

    else:
        # Move cursor to under username > MAC address
        post_ref = db.collection(username).document(mac_address_hex)

        # Default settings
        post_ref.set({
            'currPlant': 1,
            'distance': 30,
            'humidity': 10,
            'lightIntensity': 60,
            'moisture': 10,
            'pH': 7,
            'temperature': 28
        })

        # Add data into username > MAC > data > (data > actual data)
        now = datetime.now()
        curr = now.strftime("%d-%m-%Y %H:%M:%S")
        data_ref = post_ref.collection(data).document(curr)

        data_ref.set({
            'distance': 30,
            'humidity': 10,
            'lightIntensity': 60,
            'moisture': 10,
            'pH': 7,
            'temperature': 28
        })

        mainSys(username)
            
            
            
# ----------------------------------------------------------------------------------
#JUZ EXAMPLE
#Run relay and water sensor

                                  


# Connect the Grove Water Sensor to digital port D2
# SIG,NC,VCC,GND
water_sensor = 2
led = 3
relay = 14
pinMode(water_sensor,"INPUT")
pinMode(led, "OUTPUT")
pinMode(relay, "OUTPUT")

while True:
    try:
        time.sleep(0.1)
        waterlvl10 = digitalRead(water_sensor)
        
        # if water level < 10, turn off relay(water pump) & light up led
        if (waterlvl10 == 1):
            print("low water level, please refill water")
            digitalWrite(relay,1)
            digitalWrite(led, 0)
        else:
            digitalWrite(relay,0)
        time.sleep(1)
    except IOError:
        print("Error")


# ----------------------------------------------------------------------------------------








# # Rfid Function -------------- 
# def read_rfid():
#     cont = "b''"
#     print("Place your tag")
#     # store in secret and gone after 10s
#     while(cont == "b''"):
#         # read rfid value
#         register_iden = str(rpiser1.read(14))
#         if str(register_iden) != cont:
#             print(register_iden)

#             # Store rfid value into database
#             db.collection('currentUser').collection('curr').update({'rfid': register_iden})
#             time.sleep(10)
            
#             #Clear secret
#             register_iden = "b''"
#             print(register_iden)

# # Login Function --------------          
# def login():
#     print("Login")
#     login_iden = str(rpiser1.read(14))

#     #Webapp
#     #Work with webapp to match with username
#     #Login if match

#     while(login_iden == "b''"):
#         login_iden = str(rpiser1.read(14))
#         if login_iden == str(b'\x022300A4F1EB9D\x03'):
#             print("successfully login")
#             mainSys()
            