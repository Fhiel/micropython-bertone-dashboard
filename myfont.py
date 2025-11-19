# myfont.py (MicroPython - Endgültige, reine VLSB-Shift-Logik)

import framebuf
# Importiere die generierten Binärdaten
from font_large_data import FONT_LARGE_DATA 
from font_small_data import FONT_SMALL_DATA 

class MyFont:
    def __init__(self, size):
        if size == 'large':
            self.width = 16
            self.height = 21
            self.font_data = FONT_LARGE_DATA
        elif size == 'small':
            self.width = 12
            self.height = 16 # 16px Höhe = 2 Pages
            self.font_data = FONT_SMALL_DATA 
        else:
            raise ValueError("Ungültige Font-Größe")
        
        # Berechne die benötigte Bytegröße pro Zeichen
        self.bytes_per_char = self.width * ((self.height + 7) // 8)
        self.space_data = b'\x00' * self.bytes_per_char

    # --- Endgültige, REINE manuelle Kopierlogik (Standard VLSB) ---
    # Diese Logik wurde im test_single_file_font.py verifiziert.
    def text(self, text, x, y, color=1, display=None):
        if display is None or not hasattr(display, 'buffer'):
            return

        display_buffer = display.buffer
        display_width = display.width
        
        # 1. Vertikale Adressierung
        page_start = y // 8
        page_end = (y + self.height - 1) // 8
        y_offset = y % 8
        bytes_per_col = (self.height + 7) // 8
        
        # Max Display Page zur Begrenzung der Schleife
        display_max_page = (display.height // 8) - 1

        # --- Hauptschleife über die Zeichen ---
        for char in str(text):
            final_data = self.font_data.get(char, self.space_data)
            
            # --- Schleife über die Spalten des Zeichens ---
            for char_col_idx in range(self.width):
                
                # 2. X-ADRESSIERUNG: KEINE Spiegelung mehr nötig, da der Konverter dies nicht tut
                # Daten werden L-R abgerufen
                source_col_idx = char_col_idx
                
                target_x = x + char_col_idx
                
                if target_x >= display_width:
                    break
                    
                font_data_index_base = source_col_idx * bytes_per_col
                
                # --- Page-Schleife (Y-Achse): Läuft über die Display-Pages, die das Zeichen berührt ---
                # Begrenzt auf die tatsächliche Display-Höhe
                for page in range(page_start, min(page_end + 1, display_max_page + 1)):
                    
                    logical_font_page_idx = page - page_start
                    current_page_data = 0
                    
                    # 1. Haupt-Teil: Lese das aktuelle Font-Byte und wende den Haupt-Shift an
                    if logical_font_page_idx < bytes_per_col: 
                        data_byte_index = font_data_index_base + logical_font_page_idx
                        
                        if data_byte_index < len(final_data):
                            font_byte = final_data[data_byte_index]
                            
                            if y_offset == 0:
                                current_page_data |= font_byte
                            else:
                                # Haupt-Shift: Bits des aktuellen Byte, die nach oben verschoben werden
                                current_page_data |= (font_byte << y_offset) & 0xFF 

                    # 2. Überlauf: Bits von der VORHERIGEN Page, die nach unten überlaufen
                    if y_offset > 0 and logical_font_page_idx > 0:
                        
                        prev_logical_page_idx = logical_font_page_idx - 1
                        
                        if prev_logical_page_idx < bytes_per_col:
                            
                            prev_data_byte_index = font_data_index_base + prev_logical_page_idx
                            
                            if prev_data_byte_index < len(final_data):
                                prev_font_byte = final_data[prev_data_byte_index]
                                
                                # Überlauf-Shift: Bits der vorherigen Page, die nach unten überlaufen
                                current_page_data |= prev_font_byte >> (8 - y_offset)
                                
                    # --- Schreiblogik (Nur schreiben, wenn Daten vorhanden sind) ---
                    if current_page_data > 0:
                        display_index = page * display_width + target_x
                        
                        if display_index < len(display_buffer):
                            if color == 1:
                                display_buffer[display_index] |= current_page_data 
                            elif color == 0:
                                display_buffer[display_index] &= ~current_page_data
            
            x += self.width