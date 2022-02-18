"""
================================================================================
 * @file 	jetson_gpio.py
 * @author 	Mitch Manning - s4532126
 * @date 	16-07-2021
 * @brief 	Functions which relate to the init, deinit and toggle of gpio pins 
 *          on the Jetson Nano to restart the AWR1843.
================================================================================
"""
# Standard
import time
# Non-Standard 
import Jetson.GPIO as GPIO # 'Jetson.GPIO'


# Pin Names and States
NRESET          = 18
AWR_ACTIVE      = GPIO.LOW
AWR_RESET       = GPIO.HIGH


def init_gpio():
    """
    @brief  Inits the GPIO pins on the Jetson Nano.
    @param  None
    @return None
    """
    GPIO.setwarnings(False)
    GPIO.cleanup()
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(NRESET, GPIO.OUT, initial=AWR_ACTIVE)

def deinit_gpio():
    """
    @brief  Deinits the GPIO pins on the Jetson Nano.
    @param  None
    @return None
    """
    GPIO.cleanup()
    GPIO.setwarnings(True)

def toggle_gpio():
    """
    @brief  Toggles the GPIO pin on the Jetson Nanop to restart the AWR1843.
    @param  None
    @return None
    """
    GPIO.output(NRESET, AWR_RESET)
    time.sleep(0.1)
    GPIO.output(NRESET, AWR_ACTIVE)
    time.sleep(1)


if __name__ == '__main__':
    # Restart the AWR1843
    init_gpio()
    toggle_gpio()
    deinit_gpio()