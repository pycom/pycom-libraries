add_library('serial')
SERIAL_DEVICE='/dev/tty.usbmodemPy343431' 

def setup(): 
   global my_port
 
   #Connect to serial device 
   for dev in Serial.list(): 
       if dev == SERIAL_DEVICE: 
         my_port = Serial(this, dev, 115200) 
         print("Connected to '{}'".format(SERIAL_DEVICE)) 
         break 
   else: 
       msg = "Could not find serial port '{}'" 
       raise Exception(msg.format(SERIAL_DEVICE))
 
   # Clear the serial buffer and consume first 
   # line incase we missed the start of it 
   my_port.clear() 
   my_port.readStringUntil(10) 
   
   #Setup window 
   size(400, 400, P3D)

lastRoll = 0 
lastPitch = 0 

def draw(): 
   global lastRoll, lastPitch 

   #Get new reading from serial port 
   line = my_port.readStringUntil(10) 
   if line != None: 
       line = line.split(',') 
       if len(line) == 2: 
           pitch, roll = line 
           try: 
               pitch = float(pitch) 
               roll = float(roll) 
               lastPitch = pitch 
               lastRoll = roll 
           except Exception: 
               pass 

   background(0) 
   noStroke() 

   # Put view in the middle of the screen 
   # and far enough away to see properly 
   translate(width/2, height/2, -100) 

   # Default to last proper result 
   pitch = lastPitch 
   roll = lastRoll 

   # Rotate view 
   rotateX(-radians(pitch)) 
   rotateZ(radians(roll)) 
   
   # Zoom 
   scale(190) 
   
   # Draw the box 
   drawBox(0.6, 0.1, 1) 

def drawBox(w, h, d): 
   # Front 
   beginShape(QUADS) 
   fill(255,0,0) 
   vertex(-w, -h,  d) 
   vertex( w, -h,  d) 
   vertex( w,  h,  d) 
   vertex(-w,  h,  d) 
   endShape() 
   
   # Back 
   beginShape(QUADS) 
   fill(255,255,0) 
   vertex( w, -h, -d) 
   vertex(-w, -h, -d) 
   vertex(-w,  h, -d) 
   vertex( w,  h, -d) 
   endShape() 
   
   # Bottom 
   beginShape(QUADS) 
   fill( 255,0,255) 
   vertex(-w,  h,  d) 
   vertex( w,  h,  d) 
   vertex( w,  h, -d) 
   vertex(-w,  h, -d) 
   endShape() 
   
   # Top 
   img = loadImage("pycomLogoGoInventGrey800.png"); 
   blendMode(REPLACE) 
   textureMode(NORMAL) 
   textureWrap(CLAMP) 
   beginShape(QUADS) 
   texture(img) 
   tint(255,255,255) 
   vertex(-w, -h, -d, -1, -0.2) 
   vertex( w, -h, -d,  2, -0.2) 
   vertex( w, -h,  d,  2, 1.2) 
   vertex(-w, -h,  d, -1, 1.2) 
   endShape() 
   
   # Right 
   beginShape(QUADS) 
   fill(0,0,255) 
   vertex( w, -h,  d) 
   vertex( w, -h, -d) 
   vertex( w,  h, -d) 
   vertex( w,  h,  d) 
   endShape() 
   
   # Left 
   beginShape(QUADS) 
   fill(0,255,0) 
   vertex(-w, -h, -d) 
   vertex(-w, -h,  d) 
   vertex(-w,  h,  d) 
   vertex(-w,  h, -d) 
   endShape() 
