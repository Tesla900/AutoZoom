'''Main settings file'''

import json
import sys
import os

class SettingsInit:
    '''Class with JSON settings reader'''
    def __init__(self):
        try:
            # Open settings file

            #path_to_settings = str(os.environ['SCANBOT_WORKDIR'] + '/bin/settings.json')
            path_to_settings = str('settings.json')

            with open(path_to_settings) as settings_file:
                json_dict = json.load(settings_file)
                settings_file.close()

        except FileNotFoundError:
            # If file is not found
            print('Settings file is not found')
            sys.exit()

        # Init class
        self.disc_diameter_m = float(json_dict['DISC_DIAMETER_M'])
        self.sensor_wight_mm = float(json_dict['SENSOR_WIGHT_MM'])
        self.sensor_height_mm = float(json_dict['SENSOR_HEIGHT_MM'])
        self.sensor_wight_px = int(json_dict['SENSOR_WIGHT_PX'])
        self.sensor_height_px = int(json_dict['SENSOR_HEIGHT_PX'])
        self.possible_focal_length = tuple(json_dict['POSSIBLE_FOCAL_G9'])


    @staticmethod
    def modify(parameter_name, new_value):
        '''Modify settings'''

        with open('settings.json', 'w') as settings_file:
            # Load JSON
            json_dict = json.load(settings_file)

            # Write new or old parameter
            json_dict[parameter_name] = new_value

            # Write into file
            json.dump(json_dict, settings_file)

            # Close file
            settings_file.close()


if __name__ == '__main__':
    pass
