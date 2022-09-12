'''Main application file'''
import logging
import sys
from datetime import datetime
import cv2

from settings_read import SettingsInit
from zoom import Calculator
from bounds import BoundFinder

# Configure logger to write to a file
logging.basicConfig(filename='app_loggin.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

def exeptionhandler(type, value, tb):
    '''Write exeptions in log file'''
    logging.exception('Uncaught exception: {0}'.format(str(value)))

# Install exception handler
sys.excepthook = exeptionhandler

def main():
    '''Main program entry point'''
    # Import s as settings from config JSON and init calculator/bound finder clases
    s = SettingsInit()
    calculator = Calculator(s.sensor_wight_mm, s.sensor_height_mm, s.sensor_wight_px, s.sensor_height_px, s.disc_diameter_m, s.possible_focal_length)

    # Select background, object and calibration image
    calculator.select_images()

    # Select camera orientation
    calculator.select_camera_orientation()

    # Find bounds for calibration disc
    calibration_bounds = BoundFinder(calculator.background_image, calculator.calibration_image)
    processed_photo_calibration = calibration_bounds.blue_color_masking()
    #processed_photo_calibration = calibration_bounds.prepare_image(9, 100)
    _, _, disc_width, disc_height = calibration_bounds.find_object_bounds(processed_photo_calibration)

    # Calculate camera distance
    camera_distance_mm = calculator.calculate_camera_distance(disc_width, disc_height)

    # Calculate camera angle
    camera_angle_deg = calculator.calculate_camera_angle(disc_width, disc_height)

    # Process object image
    object_bounds = BoundFinder(calculator.background_image, calculator.object_image)
    processed_photo_object = object_bounds.prepare_image(9, 100)

    #If we take photo from top - camera angle > 75deg (15deg possible error error), apply cv2.HoughCircles and create mask
    mask = calibration_bounds.fill_outside_disc(camera_angle_deg)

    #Apply mask
    processed_photo_object = cv2.bitwise_and(processed_photo_object, mask)

    #Find boundings
    object_lower_x, object_lower_y, object_width_px, object_height_px = object_bounds.find_object_bounds(processed_photo_object)

    # Find big bounding box
    big_bounding_lower_x, big_bounding_lower_y, big_bounding_wight, big_bounding_height = object_bounds.find_virtual_bounds(object_lower_x, object_lower_y, object_width_px, object_height_px)

    #Save image
    bounding_image = cv2.cvtColor(processed_photo_object.copy(), cv2.COLOR_GRAY2BGR)
    cv2.rectangle(bounding_image, (big_bounding_lower_x, big_bounding_lower_y), (big_bounding_lower_x + big_bounding_wight, big_bounding_lower_y + big_bounding_height), (0, 255, 0), 3)

    cv2.imwrite('BoundingMask' + datetime.now().strftime('%H_%M_%S') + '.jpg', bounding_image)

    # Calculate real object size in mm
    object_width_mm, object_height_mm = calculator.calculate_object_size(big_bounding_wight, big_bounding_height, camera_distance_mm)

    # Calculate zoom index
    zoom = calculator.calc_zoom(big_bounding_wight, big_bounding_height, object_width_mm, object_height_mm, camera_distance_mm)

if __name__ == '__main__':
    main()
