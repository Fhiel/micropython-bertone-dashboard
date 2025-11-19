# bertone-dashboard/main.py
# Final OLED-Only Test – 3x OLED + display_manager + myfont + ssd1306

from machine import Pin, I2C, SoftI2C
import uasyncio as asyncio
import utime
import micropython
import display_manager
from ssd1306 import SSD1306_I2C
from myfont import MyFont

# Globale Variable für den Debug-Level, die den Startwert für SharedData liefert
DEBUG_LEVEL = 2 

class SharedData:
    def __init__(self):
        # Initialisierung der Daten (wie in Ihrem Entwurf)
        self.digital_speed = 0
        self.total_km = 0.0
        self.trip_km = 0.0
        self.temp_show = 1
        self.current_display_mode = display_manager.DISPLAY_MODE_SPEED
        self.current_rnd_status_char = 'P'
        self.current_contrast = 255
        self.odo_last_contrast = 0
        self.odo_dirty_flag = True
        self.last_displayed_mode = -1
        self.last_displayed_speed_str = ""
        self.last_displayed_km_str = ""
        self.last_displayed_trip_str = ""
        self.last_displayed_temp_source = -1
        self.internal_telemetry_data = {
            'motorDataValid': True, 'imdDataValid': True,
            'motorTemp': 25, 'mcuTemp': 30, 'imdIsoR': 50000
        }
        # --- Zentrale Status- und Tracking-Variablen (Fehlten) ---
        self.central_last_contrast = 0         # Contrast-Wert für Central
        self.central_dirty_flag = True         # Erzwingt den ersten vollen Redraw
        self.central_last_invert_state = 0     # Invertierungs-Status
        self.central_boot_active = True        # Wenn der Boot-Screen aktiv ist
        self.central_init_step = 0             # Schrittzähler für Boot-Animation
        self.central_ok_start_time = utime.ticks_ms() # Startzeit für Boot-Timer
       
        # --- Tracking für Central-Telemetrie (Fehlten) ---
        self.last_displayed_motor_temp = -1
        self.last_displayed_mcu_temp = -1
        self.last_displayed_imd_iso_r = -1

        # --- RND Status- und Tracking-Variablen (Fehlten) ---
        self.rnd_last_contrast = 0            # Kontrast-Tracking für RND
        self.rnd_dirty_flag = True            # Erzwingt Redraw bei Kontrastwechsel
        self.rnd_last_invert_state = 0        # Invertierungs-Status (für 'R' Gang)
        self.rnd_last_displayed_char = ' '    # Letztes angezeigtes Zeichen

        # --- ODOMETER Status- und Tracking-Variablen ---
        self.odo_last_contrast = 0            # Kontrast-Tracking
        self.odo_dirty_flag = True            # Erzwingt Redraw bei Kontrast-/Moduswechsel
        self.last_displayed_mode = -1         # Tracking des Anzeigemodus (Speed, Total, Trip, Temp)
        
        # --- Odometer Text-Tracking (zur Vermeidung unnötiger Redraws) ---
        self.last_displayed_speed_str = ""
        self.last_displayed_km_str = ""
        self.last_displayed_trip_str = ""
        self.last_displayed_temp_source = -1

        # --- Debug-Handling ---
        self.last_debug_output_time = utime.ticks_ms()
        # Nimmt den global definierten Wert als Startwert
        self.DEBUG_LEVEL = DEBUG_LEVEL 
    
    def debug_print(self, message, level=1):
        # KORRIGIERT: Nutzt self.DEBUG_LEVEL
        if self.DEBUG_LEVEL >= level: 
            if level == 1 or utime.ticks_diff(utime.ticks_ms(), self.last_debug_output_time) >= 500:
                print(f"DEBUG(main): {message}")
                self.last_debug_output_time = utime.ticks_ms()

# --------------------------------------------------------------
# HAUPTPROGRAMM
# --------------------------------------------------------------

shared = SharedData() # Erstellt das globale Datenobjekt

# --- Hardware (Longan CANBed RP2040 Pins) ---
# Hier wird die I2C-Hardware initialisiert
i2c1 = I2C(1, scl=Pin(7), sda=Pin(6), freq=400000)        # Odometer 128×32
i2c2 = SoftI2C(scl=Pin(22), sda=Pin(21), freq=400000)     # Central 128×32
i2c3 = SoftI2C(scl=Pin(24), sda=Pin(23), freq=400000)     # RND 64×32

# --- Displays initialisieren ---
odometer = SSD1306_I2C(128, 32, i2c1, addr=0x3c)
odometer.rotate(0)
central  = SSD1306_I2C(128, 32, i2c2, addr=0x3c)
central.rotate(0)
rnd = SSD1306_I2C(64, 32, i2c3, addr=0x3c)
rnd.rotate(0)

# --- display_manager zuweisen ---
display_manager.odometer = odometer
display_manager.central  = central
display_manager.rnd      = rnd

# --- Fonts laden ---
display_manager.font_small = MyFont('small')
display_manager.font_large = MyFont('large')

# --- Async Demo Loop ---
async def demo_loop(shared_data):
    # Setzt die Displays initial in den richtigen Zustand
    shared_data.current_display_mode = display_manager.DISPLAY_MODE_SPEED
    shared_data.current_rnd_status_char = 'N'
    
    await display_manager.update_odometer_display(shared_data)
    await display_manager.update_central_display(shared_data)
    await display_manager.update_rnd_display(shared_data)
    
    # --------------------------------------------------------------
    # MODUS-SIMULATION
    # --------------------------------------------------------------
    
    while True:
        # A. Geschwindigkeit anzeigen (Mode 0)
        shared_data.current_display_mode = display_manager.DISPLAY_MODE_SPEED
        shared_data.digital_speed = 78
        shared_data.current_rnd_status_char = 'D'
        shared_data.internal_telemetry_data['motorTemp'] = 65
        
        await display_manager.update_odometer_display(shared_data)
        await display_manager.update_central_display(shared_data)
        await display_manager.update_rnd_display(shared_data)
        await asyncio.sleep(2)
        
        # B. Total-Kilometer anzeigen (Mode 1)
        shared_data.current_display_mode = display_manager.DISPLAY_MODE_TOTAL
        shared_data.total_km = 123456
        shared_data.current_rnd_status_char = 'N' 
        
        await display_manager.update_odometer_display(shared_data)
        await display_manager.update_central_display(shared_data)
        await display_manager.update_rnd_display(shared_data)
        await asyncio.sleep(2)

        # C. Trip-Kilometer anzeigen (Mode 2)
        shared_data.current_display_mode = display_manager.DISPLAY_MODE_TRIP
        shared_data.trip_km = 9.4
        shared_data.current_rnd_status_char = 'R' 
        
        await display_manager.update_odometer_display(shared_data)
        await display_manager.update_central_display(shared_data)
        await display_manager.update_rnd_display(shared_data)
        await asyncio.sleep(2)

# --------------------------------------------------------------
# HAUPTPROGRAMM STARTEN
# --------------------------------------------------------------

try:
    asyncio.run(demo_loop(shared)) # shared wird übergeben
except KeyboardInterrupt:
    # Hier könnte eine Shutdown-Routine mit Contrast-Fade-Out implementiert werden
    print("\nCiao!")