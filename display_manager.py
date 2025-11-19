# display_manager.py
# display logic for Odometer, Central, and RND
# Optimized with Dirty-Rect, permanent subtext, async-safe, debug_print
# Compatible with SSD1306_I2C, myfont.py (blit version), and main.py

import utime
from myfont import MyFont

# --- Global Display Objects (set in main.py) ---
central = None
rnd = None
odometer = None

# font_small = MyFont('small')  # 12x16 Pixel : Zuweisung erfolgt in main
# font_large = MyFont('large')  # 16x21 Pixel : Zuweisung erfolgt in main

# --- Display Dimensions ---
central_width = 128
central_height = 32
odo_width = 128
odo_height = 32
rnd_width = 64
rnd_height = 32

# --- Display Modes ---
DISPLAY_MODE_SPEED = 0
DISPLAY_MODE_TOTAL = 1
DISPLAY_MODE_TRIP = 2
DISPLAY_MODE_TEMP = 3

# --- Configuration ---
CENTRAL_BOOT_DURATION_MS = 5000
R_ISO_MIN = 0
R_ISO_MAX = 50000
R_ISO_WARNING = 400
R_ISO_ERROR = 250

# --- Central Subtext: Permanent labels (drawn once) ---
_subtext_drawn = False  # Local flag: ensures subtext is drawn only once


# === ODOMETER DISPLAY (with 16x21 characters and 8x8 standard text) ===
async def update_odometer_display(shared_data):
    """
    Update the Odometer display (128x32) with speed, total km, trip, or temp source.
    Uses Dirty-Rect to update only the changed text region.
    """
    global odometer
    global font_large, font_small 

    if odometer is None:
        shared_data.debug_print("ERROR: Odometer display object is None", level=0)
        return

    # --- 1. Update contrast if changed ---
    if shared_data.current_contrast != shared_data.odo_last_contrast:
        odometer.contrast(shared_data.current_contrast)
        shared_data.odo_last_contrast = shared_data.current_contrast
        shared_data.odo_dirty_flag = True

    # --- 2. Prepare data strings ---
    speed_str = f"{shared_data.digital_speed:>3}"
    km_str = f"{int(shared_data.total_km):06d}"
    
    # NEUE Y-KOORDINATE für 21px hohe Fonts: (32 - 21) // 2 = 5
    Y_LARGE_FONT = 5
    
    # --- 3. Mode handling ---
    mode = shared_data.current_display_mode
    char_changed = False
    dirty_x0, dirty_y0 = 128, 32  # Start with invalid rect
    dirty_x1, dirty_y1 = 0, 0
    
    # Flag, ob ein vollständiger Redraw (Mode/Contrast Change) nötig ist
    full_redraw_needed = False 

    # Force full redraw on mode change
    if mode != shared_data.last_displayed_mode:
        shared_data.odo_dirty_flag = True
        shared_data.last_displayed_mode = mode

    # KORREKTUR für Überschneidungen: Bei Modus- oder Kontrastwechsel (dirty_flag=True) 
    # MUSS der gesamte Bildschirm gelöscht werden.
    if shared_data.odo_dirty_flag:
        odometer.fill(0) # Vollständiges Löschen des Buffers (128x32)
        full_redraw_needed = True
        shared_data.debug_print("Odometer: Full buffer clear due to mode/contrast change.", level=2)

    try:
        # Modes, die auf 16x21 umgestellt werden sollen
        if mode == DISPLAY_MODE_SPEED:
            X_SPEED_START = 44
            
            # Prüfe, ob neu gezeichnet werden muss (wegen Full Redraw ODER Textänderung)
            if full_redraw_needed or speed_str != shared_data.last_displayed_speed_str:
                char_changed = True
                
                # Wenn KEIN Full Redraw stattfand (nur Textänderung), müssen wir den alten Text löschen.
                if not full_redraw_needed:
                    # Nur Textänderung innerhalb des gleichen Modus: partielles Löschen
                    odometer.fill_rect(X_SPEED_START, Y_LARGE_FONT, 128 - X_SPEED_START, 21, 0)
                    odometer.fill_rect(97, 19, 8 * 4, 8, 0) # Clear unit km/h
                    
                font_large.text(speed_str, X_SPEED_START, Y_LARGE_FONT, 1, display=odometer)
                odometer.text("km/h", 97, 19) 
                
                shared_data.last_displayed_speed_str = speed_str
                
                # Dirty rect für partielles Update, falls nur Text geändert wurde
                dirty_x0, dirty_x1 = X_SPEED_START, 127 
                dirty_y0, dirty_y1 = Y_LARGE_FONT, 31 
                
        elif mode == DISPLAY_MODE_TOTAL:
            X_TOTAL_START = 0 
            if full_redraw_needed or km_str != shared_data.last_displayed_km_str:
                char_changed = True
                
                if not full_redraw_needed:
                    # Nur Textänderung innerhalb des gleichen Modus: partielles Löschen
                    odometer.fill_rect(0, Y_LARGE_FONT, 128, 21, 0) # Clear large font area
                    odometer.fill_rect(97, 19, 8 * 2, 8, 0) # Clear unit km
                
                # NEU: 16x21 Font für Total-KM (6 Zeichen * 16px/Zeichen = 96px Breite)
                font_large.text(km_str, X_TOTAL_START, Y_LARGE_FONT, 1, display=odometer)
                
                # KORREKTUR: Standard 8x8 Font für die Einheit
                odometer.text("km", 100, 19)
                
                shared_data.last_displayed_km_str = km_str
                
                dirty_x0, dirty_x1 = X_TOTAL_START, 127 
                dirty_y0, dirty_y1 = Y_LARGE_FONT, 31

        elif mode == DISPLAY_MODE_TRIP:
            X_TRIP_START = 16
            trip_val = shared_data.trip_km
            trip_str = f"{trip_val:.1f}" if trip_val >= 1000 else f"{trip_val:05.1f}"
            
            if full_redraw_needed or trip_str != shared_data.last_displayed_trip_str:
                char_changed = True
                
                if not full_redraw_needed:
                    # Nur Textänderung innerhalb des gleichen Modus: partielles Löschen
                    odometer.fill_rect(X_TRIP_START, Y_LARGE_FONT, 128 - X_TRIP_START, 21, 0)
                    odometer.fill_rect(97, 19, 8 * 2, 8, 0) # Clear unit km
                
                font_large.text(trip_str, X_TRIP_START, Y_LARGE_FONT, 1, display=odometer)
                odometer.text("km", 100, 19)
                
                shared_data.last_displayed_trip_str = trip_str
                
                dirty_x0, dirty_x1 = X_TRIP_START, 127
                dirty_y0, dirty_y1 = Y_LARGE_FONT, 31

        elif mode == DISPLAY_MODE_TEMP:
            source_changed = (shared_data.temp_show != shared_data.last_displayed_temp_source)
            if full_redraw_needed or source_changed:
                char_changed = True
                
                temp_source_str = "MOTOR" if shared_data.temp_show == 1 else "MCU"
                
                if not full_redraw_needed:
                    odometer.fill_rect(0, 8, 128, 16, 0) # Clear middle-Zone (Small Font Area)
                
                # NEU: Standardaufruf mit der SMALL Font
                font_small.text(temp_source_str, 40, 8, 1, display=odometer)
                
                shared_data.last_displayed_temp_source = shared_data.temp_show
                
                dirty_x0, dirty_x1 = 40, 100
                dirty_y0, dirty_y1 = 8, 23

        # --- 4. Show only if changed, using Dirty-Rect or Full Redraw ---
        if full_redraw_needed or char_changed:
            try:
                if full_redraw_needed:
                    # Full screen redraw (z.B. Kontrast- oder Modus-Wechsel)
                    odometer.show()
                    shared_data.debug_print("Odometer: full screen update (mode/contrast)", level=2)
                else:
                    # Nur den betroffenen Textbereich aktualisieren (innerhalb des Modus)
                    # Sicherstellen, dass die Koordinaten gültig sind (Dirty Rect wird nur bei char_changed verwendet)
                    if dirty_x0 < dirty_x1 and dirty_y0 < dirty_y1:
                        odometer.show(dirty_x0, dirty_y0, dirty_x1, dirty_y1)
                        shared_data.debug_print(f"Odometer: dirty rect ({dirty_x0},{dirty_y0},{dirty_x1},{dirty_y1})", level=3)
                    else:
                         # Fallback bei ungültigem Dirty Rect (sollte nicht passieren)
                         odometer.show() 
                         shared_data.debug_print("Odometer: dirty rect fallback to full show", level=3)

                shared_data.odo_dirty_flag = False # Setze Flag auf False nach erfolgreichem Show
            except OSError as e:
                shared_data.debug_print(f"ERROR: I2C error in odometer.show(): {e}", level=0)
                odometer = None

    except Exception as e:
        shared_data.debug_print(f"ERROR in update_odometer_display: {e}", level=0)

# === CENTRAL DISPLAY ===
async def update_central_display(shared_data):
    """
    Update the Central display (128x32) with motor temp, MCU temp, and ISO-R.
    Subtext ("MOTOR", "MCU", "ISO-R") is drawn once and preserved.
    Only the top row (y=0–15) is updated → no flicker.
    """
    global central, _subtext_drawn
    if central is None:
        return

    # --- 1. Update contrast ---
    if shared_data.current_contrast != shared_data.central_last_contrast:
        central.contrast(shared_data.current_contrast)
        shared_data.central_last_contrast = shared_data.current_contrast
        shared_data.central_dirty_flag = True

    current_time = utime.ticks_ms()

    # --- BOOT SEQUENCE ---
    if shared_data.central_boot_active:
        if utime.ticks_diff(current_time, shared_data.central_ok_start_time) > CENTRAL_BOOT_DURATION_MS:
            shared_data.central_boot_active = False
            shared_data.central_init_step = 0
            shared_data.central_dirty_flag = True
        elif shared_data.central_init_step == 0:
            central.fill_rect(0, 0, 128, 16, 0)
            shared_data.central_init_step = 1
            shared_data.central_dirty_flag = True
        elif shared_data.central_init_step == 1:
            font_small.text(" BERTONE ", 0, 0, 1, display=central)
            shared_data.central_init_step = 2
            shared_data.central_dirty_flag = True
        elif shared_data.central_init_step == 2:
            central.show()
            shared_data.central_init_step = 0
            shared_data.central_dirty_flag = False
        return

    # --- NORMAL DISPLAY ---
    # Da wir rnd.invert() für RND entfernt haben, stellen wir sicher, dass Central 
    # nicht versehentlich invertiert wurde (sollte es aber eh nicht).
    if shared_data.central_last_invert_state != 0:
        # Falls in Zukunft ein Invertierungs-Feature für Central hinzukommt, 
        # hier ggf. invert(0) aufrufen. Aktuell: nur Tracking.
        pass

    # --- Draw permanent subtext once (bottom row) ---
    if not _subtext_drawn:
        central.fill_rect(0, 16, 128, 16, 0)  # Clear bottom row
        central.text("MOTOR", 0, 18)
        central.text("MCU", 55, 18)
        central.text("ISO-R", 90, 18)
        _subtext_drawn = True
        # Show bottom row once
        try:
            central.show(0, 16, 127, 31)
            shared_data.debug_print("Central: subtext drawn permanently", level=2)
        except OSError as e:
            shared_data.debug_print(f"ERROR: I2C error in central subtext show(): {e}", level=0)

    # --- Get telemetry ---
    telemetry = shared_data.internal_telemetry_data
    motor_valid = telemetry.get('motorDataValid', False)
    imd_valid = telemetry.get('imdDataValid', False)
    motor_temp = telemetry.get('motorTemp', 0)
    mcu_temp = telemetry.get('mcuTemp', 0)
    imd_iso_r = telemetry.get('imdIsoR', 0)

    values_changed = (
        motor_temp != shared_data.last_displayed_motor_temp or
        mcu_temp != shared_data.last_displayed_mcu_temp or
        imd_iso_r != shared_data.last_displayed_imd_iso_r
    )

    # --- Update only if changed ---
    if values_changed or shared_data.central_dirty_flag:
        central.fill_rect(0, 0, 128, 16, 0)  # Clear top row only 

        motor_text = f"{motor_temp:>2d}c" if motor_valid else "--c" # c will be replaced by °C
        font_small.text(motor_text, 0, 0, 1, display=central)
        shared_data.last_displayed_motor_temp = motor_temp

        mcu_text = f"{mcu_temp:>2d}c" if motor_valid else "--c"     # ° will be replaced by °C
        font_small.text(mcu_text, 46, 0, 1, display=central)
        shared_data.last_displayed_mcu_temp = mcu_temp

        iso_text = f"{imd_iso_r // 1000:>2d}m" if imd_valid else "--m"  # ® will be replaced by MOhm for Ohm = Omega
        font_small.text(iso_text, 92, 0, 1, display=central)
        shared_data.last_displayed_imd_iso_r = imd_iso_r

        # Show only top row
        try:
            central.show(0, 0, 127, 15)
            shared_data.debug_print("Central: top row updated", level=2)
        except OSError as e:
            shared_data.debug_print(f"ERROR: I2C error in central.show(): {e}", level=0)

        shared_data.central_dirty_flag = False

# === RND DISPLAY ===
async def update_rnd_display(shared_data):
    """
    Update the RND display (64x32) with gear (R, N, D).
    Uses manual color management for local inversion of the character area only.
    Box size is 20x29 pixels.
    """
    global rnd
    global font_large 
    if rnd is None:
        return

    # --- Geometrie für 64x32 Display ---
    # Gewünschte Box-Größe: 20x29 Pixel (enthält den 16x21 Font + 2px/4px Rand)
    RND_BOX_WIDTH = 20
    RND_BOX_HEIGHT = 29
    
    # Box-Startkoordinaten (zentriert in 64x32)
    X_BOX_START = (rnd_width - RND_BOX_WIDTH) // 2 # (64 - 20) / 2 = 22
    Y_BOX_START = (rnd_height - RND_BOX_HEIGHT) // 2 # (32 - 29) / 2 = 1 (oder 2, wir nehmen 1 für die Mitte)
    
    # Text-Startkoordinaten (zentriert in der Box)
    X_TEXT_START = X_BOX_START + (RND_BOX_WIDTH - 16) // 2 # 22 + 2 = 24
    Y_TEXT_START = Y_BOX_START + (RND_BOX_HEIGHT - 21) // 2 # 1 + 4 = 5 (Perfekte Mitte)
    
    # Dirty Rect Endkoordinaten (entspricht Box-Größe)
    X_BOX_END = X_BOX_START + RND_BOX_WIDTH - 1 # 22 + 20 - 1 = 41
    Y_BOX_END = Y_BOX_START + RND_BOX_HEIGHT - 1 # 1 + 29 - 1 = 29
    
    # --- 1. Update contrast ---
    if shared_data.current_contrast != shared_data.rnd_last_contrast:
        rnd.contrast(shared_data.current_contrast)
        shared_data.rnd_last_contrast = shared_data.current_contrast
        shared_data.rnd_dirty_flag = True

    # --- 2. Determine gear character ---
    motor_data_valid = shared_data.internal_telemetry_data.get('motorDataValid', False)
    rnd_char = shared_data.current_rnd_status_char if motor_data_valid else ' '

    # --- 3. Determine colors and inversion style (Manuelle Inversion) ---
    invert_state = 1 if rnd_char == 'R' else 0
    
    if rnd_char == 'R':
        # Reverse Mode: Invertiert (Schwarzer Text auf Weißem Feld)
        char_fg_color = 0 # Text ist Schwarz
        char_bg_color = 1 # Box ist Weiß
    else:
        # Normal Mode: Normal (Weißer Text auf Schwarzem Feld)
        char_fg_color = 1 # Text ist Weiß
        char_bg_color = 0 # Box ist Schwarz (passend zum Display-Hintergrund)
        
    # Prüfen, ob der Stil (R <-> N/D) gewechselt hat, um einen Redraw zu erzwingen
    invert_changed = (shared_data.rnd_last_invert_state != invert_state)
    if invert_changed:
        shared_data.rnd_last_invert_state = invert_state
        shared_data.rnd_dirty_flag = True # Erzwinge Redraw aufgrund des Stilwechsels

    # --- 4. Update only if character or style changed ---
    char_changed = (rnd_char != shared_data.rnd_last_displayed_char)

    if char_changed or shared_data.rnd_dirty_flag:
        
        # 1. Fülle den Bereich mit der berechneten Hintergrundfarbe (0 oder 1)
        # Nutze die neuen Box-Koordinaten und -Größen
        rnd.fill_rect(X_BOX_START, Y_BOX_START, RND_BOX_WIDTH, RND_BOX_HEIGHT, char_bg_color)
        
        # 2. Zeichne den Text mit der berechneten Vordergrundfarbe (1 oder 0)
        # Nutze die neuen, zentrierten Text-Koordinaten
        font_large.text(rnd_char, X_TEXT_START, Y_TEXT_START, char_fg_color, display=rnd) 
        
        shared_data.rnd_last_displayed_char = rnd_char
        shared_data.rnd_dirty_flag = False

        # Zeige nur den 20x29 Box-Bereich (Dirty Rect)
        try:
            rnd.show(X_BOX_START, Y_BOX_START, X_BOX_END, Y_BOX_END)
            shared_data.debug_print("RND: gear updated (dirty rect, 20x29 box)", level=2)
        except OSError as e:
            shared_data.debug_print(f"ERROR: I2C error in rnd.show(): {e}", level=0)
            rnd = None