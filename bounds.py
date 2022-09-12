'''OpenCV bound detections.'''

import math
import sys

import cv2
import numpy as np

class BoundFinder:
    '''Bound detector and image preparation class.'''
    def __init__(self, background_photo, object_photo):
        self.background_photo = background_photo
        self.object_photo = object_photo

    def prepare_image(self, filter_size, filter_sigma):
        '''Get background and object photo and convert them into
        binarized object mask for bound detection.'''

        kernel = np.ones((5, 5), np.uint8)
        threshold = 10

        # Convert background photo copy and object photo copy to HSV, find the difference
        substracted_image = cv2.absdiff(self.object_photo.copy(), self.background_photo.copy())
        substracted_image = cv2.cvtColor(substracted_image, cv2.COLOR_BGR2GRAY)

        # Erode/dilate to remove noise, apply bilateral filter/blur to image to remove noise
        substracted_image = cv2.morphologyEx(substracted_image, cv2.MORPH_OPEN, kernel)
        filtered_image = cv2.bilateralFilter(substracted_image, filter_size, filter_sigma, filter_sigma)
        filtered_image = cv2.GaussianBlur(filtered_image, (3, 3), 0)

        #If intensity of a pixel is bigger than threshgold, use this pixel as a mask
        imask =  filtered_image > threshold

        #Create black canvas and white background
        canvas = np.zeros_like(self.object_photo.copy(), np.uint8)
        whiteboard = np.zeros_like(self.object_photo.copy(), np.uint8)
        whiteboard.fill(255)

        #Fill canvas with white by  image masl
        canvas[imask] = whiteboard[imask]

        #Convert canvas to grayscale and equalize histogtam
        canvas = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
        canvas = cv2.equalizeHist(canvas)

        # Apply Otsu's Binarization
        _, canvas = cv2.threshold(canvas, 10, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        #cv2.imshow("Processed", canvas)
        #cv2.waitKey(0)
        #cv2.destroyAllWindows()

        return canvas


    def find_object_bounds(self, processed_photo):
        '''Get processed thresholded photo and find object bounding box.'''

        # Find external contours for processed image

        contours, _ = cv2.findContours(processed_photo.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        popup = []

        # Find contours with area bigger than 1000 px
        for i in range(len(contours)):
            if cv2.contourArea(contours[i]) < 1000:
                popup.append(i)
            else:
                x_lower, y_lower, width, height = cv2.boundingRect(contours[i])

        for i in popup[::-1]:
            contours.pop(i)

        # Concatenate contours to one big contour
        big_contour = np.concatenate(contours)
        #big_contour = max(contours, key = cv2.cv2.contourArea)

        # Calculate boundig box for big contour
        x_lower, y_lower, width, height = cv2.boundingRect(big_contour)

        # Return lower corner coordinates and width/height for bounding box
        return (x_lower, y_lower, width, height)

    def fill_outside_disc(self, angle):
        '''This function detect gray disc edge and return mask to fill all outside of work disc with black (to remove noise) if camera angle > 75deg'''
        if angle > 60.0:
            # Convert background photo copy to grayscale
            background_gray = cv2.cvtColor(self.background_photo.copy(), cv2.COLOR_BGR2GRAY)
            background_gray = cv2.resize(background_gray, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_CUBIC)

            # detect circles in the image
            circles = cv2.HoughCircles(background_gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100, minRadius=150)

            # ensure at least some circles were found
            if circles is not None:
                # convert the (x, y) coordinates and radius of the circles to integers and multiply back on 1/scale_coef
                circles = np.round(circles[0, :]).astype('int')
                circles = circles * 2

                #Find circle with biggest radius, apply 120 px margin
                biggest_circle = circles[np.argmax(circles[:, 2])]

                xc, yc, radius = biggest_circle[0], biggest_circle[1], biggest_circle[2]-120

                #Create filtering mask with circle (draw white filled circle on black background as mask)
                filter_mask = np.zeros_like(self.object_photo)
                filter_mask = cv2.circle(filter_mask, (xc, yc), radius, (255, 255, 255), -1)
                filter_mask = cv2.cvtColor(filter_mask, cv2.COLOR_BGR2GRAY)
            else:
                #Create array of 255 to let code flow properly
                filter_mask = np.zeros_like(self.object_photo.copy(), np.uint8)
                filter_mask.fill(255)
        else:
            #Create array of 255 to let code flow properly
            filter_mask = np.zeros_like(self.object_photo.copy(), np.uint8)
            filter_mask.fill(255)
        return filter_mask

    def blue_color_masking(self):
        '''Create mask to ignore all non-blue objects'''

        # Create copy of blue disc image for safe processing and convert to HSV format
        loaded_image = self.object_photo.copy()

        blue_disc_image = cv2.cvtColor(loaded_image, cv2.COLOR_BGR2HSV)

        # Apply bilateral filter/blur to image to remove noise
        blue_disc_image = cv2.GaussianBlur(blue_disc_image, (3, 3), 0)
        blue_disc_image = cv2.bilateralFilter(blue_disc_image, 9, 75, 75)

        # Range for blue color (OpenCV uses H: 0-179, S: 0-255, V: 0-255 instead of H = 0-360, S = 0-100 and V = 0-100)
        lower_blue = np.array([100, 80, 80])
        upper_blue = np.array([145, 255, 255])

        # Create mask
        mask = cv2.inRange(blue_disc_image, lower_blue, upper_blue)

        # Morfological processing for the mask
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, np.ones((3, 3), np.uint8))

        #cv2.imshow("mask", mask)
        #cv2.waitKey(0)
        #cv2.destroyAllWindows()

        return mask



    def find_virtual_bounds(self, small_bounding_lower_x, small_bounding_lower_y, small_bounding_wight, small_bounding_height):
        '''Find big virtual bounding box for biased object. Also perfom a check if object is not centered properly'''
        try:
            # Find image center
            image_center_y, image_center_x, _ = tuple(ti/2 for ti in self.object_photo.shape)

            # Check if object is centered. Assepted base margin is 300px for any object. If object is bigger - allow bigger margin
            # 1) Find center for object bounding box
            object_center_x = small_bounding_lower_x + small_bounding_wight / 2
            object_center_y = small_bounding_lower_y + small_bounding_height / 2

            # 2) Calculate maximal allowed margin as 20% of object side. We use smaller side of object for calculations. If margin < treshold, margin = treshhold
            allowed_margin = min(small_bounding_wight, small_bounding_height) * 0.2 if min(small_bounding_wight, small_bounding_height) * 0.2 > 400 else 400

            # 3) Calculate distance between image center and object center
            distance_from_center = math.sqrt((object_center_x - image_center_x)**2 + (object_center_y - image_center_y))

            # 4) Perform check if distance is lower then allowed margin
            if distance_from_center > allowed_margin:
                print('Object on photo is biased. Please, double-check the setup and start again or make photo if you sure that all OK')
            else:
                print('Object is centered properly')

            # Find top points for small bounding box
            small_bounding_points = {}
            small_bounding_points['1'] = (small_bounding_lower_x, small_bounding_lower_y)
            small_bounding_points['2'] = (small_bounding_lower_x + small_bounding_wight, small_bounding_lower_y)
            small_bounding_points['3'] = (small_bounding_lower_x + small_bounding_wight, small_bounding_lower_y + small_bounding_height)
            small_bounding_points['4'] = (small_bounding_lower_x, small_bounding_lower_y + small_bounding_height)

            # Find most distance top point from center
            max_distance = 0
            for point in small_bounding_points:
                bounding_x, bounding_y = small_bounding_points[point]
                distance = math.sqrt((bounding_x - image_center_x)**2 + (bounding_y - image_center_y)**2)
                if distance > max_distance:
                    max_distance = distance
                    max_point_x, max_point_y = small_bounding_points[point]

            # Calculate wight/heigth for new big bounding bor
            big_bounding_wight = int(2 * abs(max_point_x - image_center_x))
            big_bounding_height = int(2 * abs(max_point_y - image_center_y))

            # Find bottom-left point of big bounding
            big_bounding_lower_x = int(image_center_x - big_bounding_wight / 2)
            big_bounding_lower_y = int(image_center_y - big_bounding_height / 2)

            return  (big_bounding_lower_x, big_bounding_lower_y, big_bounding_wight, big_bounding_height)

        except (ArithmeticError, ValueError):
            print('Big bounding box calculation error')
            sys.exit()

if __name__ == '__main__':
    pass
