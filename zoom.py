'''OpenCV get camera angle, distance, FOV.'''

import sys
import math
import argparse

import cv2

class Calculator:
    '''Main zoom calculator class.'''
    def __init__(self, sensor_wight_mm, sensor_height_mm, sensor_wight_px, sensor_height_px, disc_diameter_m, possible_focal_length):
        self.sensor_wight_mm = sensor_wight_mm
        self.sensor_height_mm = sensor_height_mm
        self.sensor_wight_px = sensor_wight_px
        self.sensor_height_px = sensor_height_px
        self.disc_diameter_m = disc_diameter_m

        self.calibration_image = None
        self.background_image = None
        self.object_image = None
        self.serial_number = None

        self.zoom_index = 0
        self.possible_focal_length = possible_focal_length

    def select_images(self):
        '''Get calibration, background and obrect image(temp funciton).'''
        # Select directory, normalize path
        try:
            #Add
            parser = argparse.ArgumentParser(description='Photo select')
            parser.add_argument('--blue', type=str, default='None', help='Blue disc photo name(default: None)')
            parser.add_argument('--gray', type=str, default='None', help='Gray disc photo name (default: None)')
            parser.add_argument('--obj', type=str, default='None', help='Object photo name (default: None)')
            parser.add_argument('--sn', type=str, default='None', help='Camera serial number (default: None)')
            args = parser.parse_args()

            # Generate path to the selected files
            path_to_calibration_image = str(args.blue)
            path_to_background_image = str(args.gray)
            path_to_object_image = str(args.obj)

            # Read the images with OpenCV and save calibration and background image
            self.calibration_image = cv2.imread(path_to_calibration_image)
            self.background_image = cv2.imread(path_to_background_image)
            self.object_image = cv2.imread(path_to_object_image)
            self.serial_number = str(args.sn)

        except FileNotFoundError:
            print('File is not found')
            sys.exit()

    def select_camera_orientation(self):
        '''Select camera orientation'''
        height, width, _ = self.calibration_image.shape

        if height > width:
            self.sensor_wight_mm, self.sensor_height_mm = self.sensor_height_mm, self.sensor_wight_mm
            self.sensor_wight_px, self.sensor_height_px = self.sensor_height_px, self.sensor_wight_px


    def calculate_camera_distance(self, calibration_wight_px, calibration_height_px):
        '''Get distance to blue disc, mm.'''
        try:

            #Find pixel destiny
            px_dest_wight = self.calibration_image.shape[0]/self.sensor_wight_mm
            px_dest_height = self.calibration_image.shape[1]/self.sensor_height_mm

            # Calculate disc width/height on sensor (mm)
            disc_width_on_sensor = calibration_wight_px/px_dest_wight
            disc_height_on_sensor = calibration_height_px/px_dest_height

            #Calculate distance to disc using wight and height. Take mean
            distance1 = self.possible_focal_length[0]*(disc_width_on_sensor + self.disc_diameter_m*1000)/disc_width_on_sensor
            distance2 = self.possible_focal_length[0]*(disc_height_on_sensor + self.disc_diameter_m*1000)/disc_width_on_sensor
            mean_distance = (distance1 + distance2)/2

            #print('Camera distance is: ', mean_distance)

        except (ArithmeticError, ValueError):
            print('Calculation error (camera distance)')
            sys.exit()

        return mean_distance

    def calculate_object_size(self, object_width_px, object_height_px, distance_to_object):
        '''Calculate object size.'''
        try:
            #Find pixel destiny
            px_dest_wight = self.calibration_image.shape[0] / self.sensor_wight_mm
            px_dest_height = self.calibration_image.shape[1] / self.sensor_height_mm

            # Calculate object width/height on sensor (mm)
            object_width_on_sensor = object_width_px / px_dest_wight
            object_height_on_sensor = object_height_px / px_dest_height

            # Calculate real object size (mm)
            object_width = object_width_on_sensor*(distance_to_object-self.possible_focal_length[0])/self.possible_focal_length[0]
            object_height = object_height_on_sensor*(distance_to_object-self.possible_focal_length[0])/self.possible_focal_length[0]

        except (ArithmeticError, ValueError):
            print('Calculation error (object size)')
            sys.exit()

        return (object_width, object_height)

    def calculate_camera_angle(self, calibration_wight, calibration_height):
        '''Get camera angle using calibration object wight and height.'''
        # Try to calculate angle
        # Let's assume if camera angle is in between 0 < a < 60 - we make horisontal photo (bottle/vertical box/etc)
        # If camera angle is in berween 60 < a < 90 - we will take straight shoot from top of the scanbot
        try:
            angle = (180/math.pi)*math.asin(min(calibration_height, calibration_wight)/max(calibration_height, calibration_wight))

            if angle <= 75.0:
                print('Camera angle is: ', angle)

            elif angle > 75.0:
                print('Camera angle is 90, straight photo:')

            return angle

        except (ArithmeticError, ValueError):
            print('Calculation error (object size)')
            sys.exit()

    def calc_zoom(self, object_width_px, object_height_px, object_width_mm, object_height_mm, distance_to_object):
        '''Get proper zoom value'''
        try:
            #Find pixel destiny
            px_dest_wight = self.sensor_wight_px / self.sensor_wight_mm
            px_dest_height = self.sensor_height_px / self.sensor_height_mm

            # Calculate estimated object width/height on sensor (mm). Object must fill 80% of image
            object_height_on_sensor = 0.8 * self.sensor_height_px / px_dest_height
            object_wight_on_sensor = 0.8 * self.sensor_wight_px / px_dest_wight

            # Calculate used side of object:
            if self.sensor_wight_px > self.sensor_height_px:
                if(object_width_px > object_height_px) and ((object_width_px / object_height_px) > (self.sensor_wight_mm / self.sensor_height_mm)):
                    object_size_on_sensor = object_wight_on_sensor
                    object_size_mm = object_width_mm
                else:
                    object_size_on_sensor = object_height_on_sensor
                    object_size_mm = object_height_mm
            else:
                if (object_width_px < object_height_px) and ((object_height_px / object_width_px) > (self.sensor_height_mm / self.sensor_wight_mm)):
                    object_size_on_sensor = object_height_on_sensor
                    object_size_mm = object_height_mm
                else:
                    object_size_on_sensor = object_wight_on_sensor
                    object_size_mm = object_width_mm

            # Calculate estimated focal (mm)
            estimated_focal = (object_size_on_sensor * distance_to_object)/(object_size_mm + object_size_on_sensor)

        except (ArithmeticError, ValueError):
            print('Calculation error (zoom coef)')
            sys.exit()

        #Find closest lower zoom value in list
        focal = min([i for i in self.possible_focal_length if i < estimated_focal], key=lambda x: abs(x-estimated_focal))
        zoom_index = self.possible_focal_length.index(focal) + 1

        #print('Estimated focal is {}'.format(estimated_focal))
        #print('Camera focal is {}. Zoom index is {}.'.format(focal, zoom_index))

        #write zoom into file
        zoomfile = open('zoom.conf', 'w')
        zoomfile.write(self.serial_number + '=' + str(zoom_index))
        zoomfile.close()

        return zoom_index

if __name__ == '__main__':
    pass
