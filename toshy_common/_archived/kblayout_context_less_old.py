#!/usr/bin/env python3

import os
import sys
import signal
import platform
from xkbcommon import xkb

# Set up logging
VERBOSE = True
FLUSH = True

def debug(*args, ctx="DD"):
    if not VERBOSE:
        return
    if len(args) == 0 or (len(args) == 1 and args[0] == ""):
        print("", flush=FLUSH)
        return
    print(f"({ctx})", *args, flush=FLUSH)

def warn(*args, ctx="WW"):
    print(f"({ctx})", *args, flush=FLUSH)

def error(*args, ctx="EE"):
    print(f"({ctx})", *args, flush=FLUSH)

def info(*args, ctx="--"):
    print(f"({ctx})", *args, flush=FLUSH)

# Signal handling
def signal_handler(sig, frame):
    if sig in (signal.SIGINT, signal.SIGQUIT):
        print('\n')
        debug(f'Signal {sig} received. Cleaning up and exiting.\n')
        sys.exit(0)

# Set up signal handling
if platform.system() != 'Windows':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler) 
    signal.signal(signal.SIGHUP, signal_handler)
else:
    error(f'This is only meant to run on Linux. Exiting.')
    sys.exit(1)

class KeymapAnalyzer:
    """Analyzes an XKB keymap to map keysyms to required modifiers"""
    
    def __init__(self):
        self.context = xkb.Context()
        self.keymap = None
        self.layout_name = None
        
    def load_keymap_from_names(self, rules=None, model=None, layout=None, 
                              variant=None, options=None):
        """Load a keymap from RMLVO names"""
        try:
            self.keymap = self.context.keymap_new_from_names(
                rules=rules,
                model=model,
                layout=layout,
                variant=variant,
                options=options
            )
            self.layout_name = self.keymap.layout_get_name(0)
            info(f"Loaded keymap for layout: {self.layout_name}")
        except Exception as e:
            error(f"Failed to load keymap: {e}")
            return False
        return True

    def analyze_key(self, keycode):
        """Analyze a single key's levels and modifiers"""
        if not self.keymap:
            error("No keymap loaded")
            return None
            
        try:
            key_name = self.keymap.key_get_name(keycode)
            debug(f"\nAnalyzing key {key_name} (keycode {keycode}):")
            
            layout_idx = 0  # Using first layout
            results = []
            
            # Get number of shift levels for this key
            num_levels = self.keymap.num_levels_for_key(keycode, layout_idx)
            
            for level in range(num_levels):
                # Get keysyms for this level
                keysyms = self.keymap.key_get_syms_by_level(keycode, layout_idx, level)
                symbol_names = [xkb.keysym_get_name(ks) for ks in keysyms]
                
                # Get modifier mask required for this level
                mod_indices = self.keymap.key_get_mods_for_level(keycode, layout_idx, level)
                mod_names = []
                for idx in range(self.keymap.num_mods()):
                    for mask in mod_indices:
                        if mask & (1 << idx):
                            mod_name = self.keymap.mod_get_name(idx)
                            mod_names.append(mod_name)
                
                level_info = {
                    'level': level,
                    'symbols': symbol_names,
                    'mod_indices': mod_indices,
                    'mod_names': mod_names
                }
                results.append(level_info)
                
                debug(f"  Level {level}:")
                debug(f"    Symbols: {symbol_names}")
                debug(f"    Mod indices: {mod_indices}")
                debug(f"    Mod names: {mod_names}")
                
            return results
            
        except xkb.XKBError as e:
            error(f"XKB error analyzing keycode {keycode}: {e}")
            return None

def main():
    analyzer = KeymapAnalyzer()
    
    # Load current layout (for testing, we'll use explicit names)
    if not analyzer.load_keymap_from_names(layout='us', variant='mac'):
        sys.exit(1)
    
    # Analyze some test keys
    for keycode in range(9, 40):  # Test range covering main keys
        analyzer.analyze_key(keycode)

if __name__ == "__main__":
    main()
