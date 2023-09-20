# Grovepi libraries ------------------------------------
import time
from grovepi import *
from queue import Queue
import threading
from grove_rgb_lcd import *

# RFID libraries
import serial
rpiser1 = serial.Serial('/dev/ttyS0',
                       baudrate=9600, timeout=1,
                       bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                       xonxoff=False, rtscts=False, dsrdtr=False) #RPISER port
rpiser1.flushInput()
rpiser1.flushOutput()


# List of sensors ===================================
dhtSensor = 7          # D7
lightSensor = 15       # A1
moistureSensor = 16    # A2
water_sensor = 2       # D2
led_light = 8          # D8
led_temp = 5           # D5
led_hum = 6            # D6
led_pump = 3           # D3
relayForPump = 14      # A0
relayForLight = 4      # D4

pinMode(lightSensor, "INPUT")
pinMode(dhtSensor, "INPUT")
pinMode(moistureSensor, "INPUT")
pinMode(led_light, "OUTPUT")
pinMode(led_temp, "OUTPUT")
pinMode(led_hum, "OUTPUT")
pinMode(led_pump, "OUTPUT")
pinMode(relayForPump, "OUTPUT")
pinMode(relayForLight, "OUTPUT")
# ------------------------------------------------------


# Function for reading data (multithread) --------------
def sensor_reading_loop(sensor_queue):
    while True:
        try:
            # Read sensor data ========================
            [temp, hum] = dht(dhtSensor, 0)
            light = analogRead(lightSensor)
            moisture = analogRead(moistureSensor)
            distance = ultrasonicRead(ultrasonic)
            
            # Put sensor data into a dictionary key value pair and pass it into thread queue
            sensor_data = {
                "temperature": temp,
                "humidity": hum,
                "light_intensity": light,
                "soil_moisture": moisture,
                "distance": distance
            }
            
            sensor_queue.put(sensor_data)
            
            time.sleep(1) # Read data every second (Modifiable)
            # ========================================
        # Exceptions =================================
        except KeyboardInterrupt:
            print("Sensor Reading Program Exited")
            break
        except TypeError:
            print("Type Error occurs")
        except IOError:
            print("IO error occurs")
        # ============================================
# -----------------------------------------------------



# Reg Function -------------- 
def register():
    cont = "b''"
    print("Place your tag")
    # store in secret and gone after 10s
    while(cont == "b''"):
        register_iden = str(rpiser1.read(14))
        if str(register_iden) != cont:
            print(register_iden)
            print("Boleh Masuk")
            time.sleep(10)
            #Clear secret
            register_iden = "b''"
            print(register_iden)

# Login Function --------------          
def login():
    print("Login")
    login_iden = str(rpiser1.read(14))

    #Webapp
    #Work with webapp to match with username
    #Login if match

    while(login_iden == "b''"):
        login_iden = str(rpiser1.read(14))
        if login_iden == str(b'\x022300A4F1EB9D\x03'):
            print("successfully login")
            mainSys()
            
    
# tempHum Function --------------   
def tempHum(temp, hum, moist, light):
    # get threshold from firestore
    threshold = 20
    
    if ((temp >= threshold) and (hum >= threshold)):
        print("Turn on")
        #To alert user that the threshold has been hit for the plant
        digitalWrite(led_pump, 0)
        #Run lightIntensity Module
        lightIntensity(light)
    else:
        print("Turn off")
        #Off lights, haven't cross threshold
        digitalWrite(led_pump, 1)
        #Run soilMoisture Module
        soilMoist(moist)
        
# soilMoist Function --------------    
def soilMoist(moisture):
    #Example only, will need to get from Firebase
    threshold = 5
    
    if moisture != threshold:
        print("Low moisture")
        waterLevel()
        #Tell user that there's low moisture level in soil
        digitalWrite(led_pump, 1)
    else:
        print("Enough moisture")
        
# lightIntensity Function -------------- 
def lightIntensity(light):
    threshold = 300
    if light >= threshold:
        print("High Light Intensity Detected!!")
        #turn off light bulb
        digitalWrite(led_pump, 0)
        #turn on light shade
        #code for an actuator
    else:
        print("Low Light Intensity Detected!!")
        #Turn on light bulb
        digitalWrite(led_pump, 1)
    
# waterLevel Function --------------         
def waterLevel():
    waterlvl = grovepi.digitalRead(water_sensor)
    # if water level < 10, turn off relay(water pump) & light up led
    # waterSensor, 0 = got, 1 = no have
    if (waterlvl == 1):
        print("low water level, please refill water")
        #off signifies that the water is sufficient
        digitalWrite(led_pump, 1)
    else:
        #show that enough water to run pump
        digitalWrite(led_pump, 0)
        #open relay for water pump
        grovepi.digitalWrite(relay,1)
    time.sleep(1)

# Main System to run Function?? --------------     
# Might be replaced by sensor reading loop? --------------      
def mainSys():
    cont = True
    digitalWrite(led_pump, 1)
    while cont:
         # read value(temp,humidty) from dhtsensor
        [temp, hum] = dht(dhtSensor, 0)
        light = analogRead(lightSensor)
        moist = analogRead(moistureSensor)
        print("Temp = %.2f, hum = %.2f, light = %d, moisture = %d" %(temp, hum, light,moist))
        
        # convert to string
        t = str(temp)
        h = str(hum)
        l = str(light)
        m = str(moist)
        
        #print on the LCD screen for real time display
        setRGB(0, 255, 0)
        setText("T=" + t + "\337" + "C   H=" +  h + "%" + "L=" + l + "  M=" + m)
        
        
        # store temp, hum, light and moist into firestore
        
        # call temperature and humidity module
        tempHum(temp,hum, moist, light)
        
        # ============================================
# -----------------------------------------------------


# Main program ----------------------------------------------------------------------------
if __name__ == "__main__":
    # ===================================================
    # Menu
    # while True:
    #     print("1. Register")
    #     print("2. Login")
    #     choice = input("Enter: ")
        
    #     if choice == "1":
    #         register()
    #     elif choice == "2":
    #         login()
        mainSys()
            
            
            
# ----------------------------------------------------------------------------------
#JUZ EXAMPLE
#Run relay and water sensor
import time
import grovepi                                    


# Connect the Grove Water Sensor to digital port D2
# SIG,NC,VCC,GND
water_sensor = 2
led = 3
relay = 14
grovepi.pinMode(water_sensor,"INPUT")
grovepi.pinMode(led, "OUTPUT")
grovepi.pinMode(relay, "OUTPUT")

while True:
    try:
        time.sleep(0.1)
        waterlvl10 = grovepi.digitalRead(water_sensor)
        
        # if water level < 10, turn off relay(water pump) & light up led
        if (waterlvl10 == 1):
            print("low water level, please refill water")
            grovepi.digitalWrite(relay,1)
            grovepi.digitalWrite(led, 0)
        else:
            grovepi.digitalWrite(relay,0)
        time.sleep(1)
    except IOError:
        print("Error")


# ----------------------------------------------------------------------------------------