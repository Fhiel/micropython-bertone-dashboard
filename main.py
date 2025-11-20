# Final OLED-Only Test – 3x OLED + display_manager + myfont + ssd1306

from machine import Pin, I2C, SoftI2C
import uasyncio as asyncio
import utime
import micropython
import display_manager
from ssd1306 import SSD1306_I2C
from myfont import MyFont

# Global variable for the debug level, providing the starting value for SharedData
DEBUG_LEVEL = 2 

class SharedData:
    def __init__(self):
        # Data initialization (as in your draft)
        self.digital_speed = 0
        self.total_km = 0.0
        self.trip_km = 0.0
        self.temp_show = 1
        self.current_display_mode = display_manager.DISPLAY_MODE_SPEED
        self.current_rnd_status_char = 'P'
        self.current_contrast = 255
        
        # --- Central Status and Tracking Variables (Missing) ---
        self.central_last_contrast = 0         # Contrast value for Central
        self.central_dirty_flag = True         # Forces the first full redraw
        self.central_last_invert_state = 0     # Inversion status
        self.central_boot_active = True        # When the boot screen is active
        self.central_init_step = 0             # Step counter for boot animation
        self.central_ok_start_time = utime.ticks_ms() # Start time for boot timer
        
        # --- Tracking for Central Telemetry (Missing) ---
        self.internal_telemetry_data = {
            'motorDataValid': True, 'imdDataValid': True,
            'motorTemp': 25, 'mcuTemp': 30, 'imdIsoR': 50000
        }
        self.last_displayed_motor_temp = -1
        self.last_displayed_mcu_temp = -1
        self.last_displayed_imd_iso_r = -1

        # --- RND Status and Tracking Variables (Missing) ---
        self.rnd_last_contrast = 0             # Contrast tracking for RND
        self.rnd_dirty_flag = True             # Forces redraw upon contrast change
        self.rnd_last_invert_state = 0         # Inversion status (for 'R' gear)
        self.rnd_last_displayed_char = ' '     # Last displayed character

        # --- ODOMETER Status and Tracking Variables ---
        self.odo_last_contrast = 0             # Contrast tracking
        self.odo_dirty_flag = True             # Forces redraw upon contrast/mode change
        self.last_displayed_mode = -1          # Tracking of the display mode (Speed, Total, Trip, Temp)
        
        # --- Odometer Text Tracking (to avoid unnecessary redraws) ---
        self.last_displayed_speed_str = ""
        self.last_displayed_km_str = ""
        self.last_displayed_trip_str = ""
        self.last_displayed_temp_source = -1

        # --- Debug Handling ---
        self.last_debug_output_time = utime.ticks_ms()
        # Uses the globally defined value as initial value
        self.DEBUG_LEVEL = DEBUG_LEVEL 
    
    def debug_print(self, message, level=1):
        # CORRECTED: Uses self.DEBUG_LEVEL
        if self.DEBUG_LEVEL >= level: 
            # Only print often if level is 1 (high priority)
            if level == 1 or utime.ticks_diff(utime.ticks_ms(), self.last_debug_output_time) >= 500:
                print(f"DEBUG(main): {message}")
                self.last_debug_output_time = utime.ticks_ms()

# --------------------------------------------------------------
# MAIN PROGRAM
# --------------------------------------------------------------

shared = SharedData() # Creates the global data object

# --- Hardware (Longan CANBed RP2040 Pins) ---
# I2C hardware initialization happens here
i2c1 = I2C(1, scl=Pin(7), sda=Pin(6), freq=400000)      # Odometer 128×32
i2c2 = SoftI2C(scl=Pin(22), sda=Pin(21), freq=400000)  # Central 128×32
i2c3 = SoftI2C(scl=Pin(24), sda=Pin(23), freq=400000)  # RND 64×32

# --- Initialize Displays ---
odometer = SSD1306_I2C(128, 32, i2c1, addr=0x3c)
odometer.rotate(0)
central  = SSD1306_I2C(128, 32, i2c2, addr=0x3c)
central.rotate(0)
rnd = SSD1306_I2C(64, 32, i2c3, addr=0x3c)
rnd.rotate(0)

# --- Assign display_manager targets ---
display_manager.odometer = odometer
display_manager.central  = central
display_manager.rnd      = rnd

# --- Load Fonts ---
display_manager.font_small = MyFont('small')
display_manager.font_large = MyFont('large')

# --- Async Demo Loop ---
async def demo_loop(shared_data):
    # Sets the displays initially to the correct state
    shared_data.current_display_mode = display_manager.DISPLAY_MODE_SPEED
    shared_data.current_rnd_status_char = 'N'
    
    await display_manager.update_odometer_display(shared_data)
    await display_manager.update_central_display(shared_data)
    await display_manager.update_rnd_display(shared_data)
    
    # --------------------------------------------------------------
    # MODE SIMULATION
    # --------------------------------------------------------------
    
    while True:
        # A. Display Speed (Mode 0)
        shared_data.current_display_mode = display_manager.DISPLAY_MODE_SPEED
        shared_data.digital_speed = 78
        shared_data.current_rnd_status_char = 'D'
        shared_data.internal_telemetry_data['motorTemp'] = 65
        
        await display_manager.update_odometer_display(shared_data)
        await display_manager.update_central_display(shared_data)
        await display_manager.update_rnd_display(shared_data)
        await asyncio.sleep(2)
        
        # B. Display Total Kilometers (Mode 1)
        shared_data.current_display_mode = display_manager.DISPLAY_MODE_TOTAL
        shared_data.total_km = 123456
        shared_data.current_rnd_status_char = 'N' 
        
        await display_manager.update_odometer_display(shared_data)
        await display_manager.update_central_display(shared_data)
        await display_manager.update_rnd_display(shared_data)
        await asyncio.sleep(2)

        # C. Display Trip Kilometers (Mode 2)
        shared_data.current_display_mode = display_manager.DISPLAY_MODE_TRIP
        shared_data.trip_km = 9.4
        shared_data.current_rnd_status_char = 'R' 
        
        await display_manager.update_odometer_display(shared_data)
        await display_manager.update_central_display(shared_data)
        await display_manager.update_rnd_display(shared_data)
        await asyncio.sleep(2)

# --------------------------------------------------------------
# START MAIN PROGRAM
# --------------------------------------------------------------

try:
    asyncio.run(demo_loop(shared)) # shared data is passed
except KeyboardInterrupt:
    # A shutdown routine with contrast fade-out could be implemented here
    print("\nCiao!")