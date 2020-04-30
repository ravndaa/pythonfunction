'''
    @author as@virinco.com
    @brief  Vicpack parser class
'''
import re
import time
import random
import struct
import math
import ctypes
import datetime



PACKET_MEAS     = 4 # index which contains the number of measurements
PACKET_INDEX    = 2 # index which contains the packet id    
PACKET_REQUESTID= 3 # index which contains the request id
PACKET_OFFSET   = 5 # offset between measurements
PACKET_HEADER   = 5 # offset from SOP to first measurement

SAMPLE_TIME     = 2                 # sampling time measurement type
DRIVER_TYPE     = 1                 # driver measurement type
ACK_TYPE        = 126               # acknowledge type

DEFAULT_SLOT    = -1                # default slot number when unknown or async packet is received
DEFAULT_SENSOR_TYPE = 'UNKNOWN'     # default sensor type if unkwon or async packet is received

class vicpack:
    def __init__ (self):
        # configuration settings
        self.detail     = False         # detailed printout on call to print
        self.prefix     = True          # apply SI prefixes to result
        self.fullmac    = False         # display full mac-address
        self.timefmt    = '%H:%M:%S'    # time format

        # packet related variables
        self.id         = 0             # current packet id
        self.requestId  = 0             # request id
        self.meas       = 0             # total number of measurements in packet
        self.size       = 0             # size in bytes
        self.pck        = list()        # packet payload
        self.slot       = 0             # current slot where driver is located
        self.driver     = 0             # current driver type, see self.sensors for types
        self.index      = 0             # index to driver location in the node storage table
        self.enabled    = False         # driver state, enabled or disabled

        self.types = {
                    'no_measurement'            :{'fmt': 'unknown       : {:d}'                             , 'type': 0  , 'si': False, 'units': ''                 , 'function': self.__get_default},   
                    'driver_info'               :{'fmt': 'slot: {:02d}, drv: {:02d}, index: {:02d}, ena: {}', 'type': 1  , 'si': False, 'units': ''                 , 'function': self.__get_driver_info},
                    'sampling_time'             :{'fmt': '{}'                                               , 'type': 2  , 'si': False, 'units': 'sec'              , 'function': self.__get_default},
                    'sampling_time_lsb'         :{'fmt': '{}'                                               , 'type': 3  , 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'sampling_time_offset'      :{'fmt': '{}'                                               , 'type': 4  , 'si': False, 'units': 'usec'             , 'function': self.__get_default},
     
                    'internal_battery_on_die'   :{'fmt': 'on-die volt   : {:.2f}'                           , 'type': 7  , 'si': True,  'units': 'V'                , 'function': self.__get_ondie_voltage}, 
                    'internal_battery'          :{'fmt': 'battery       : {:.2f}'                           , 'type': 8  , 'si': True,  'units': 'V'                , 'function': self.__get_battery_voltage},
                    'internal_temperature'      :{'fmt': 'on-die temp   : {:.2f}'                           , 'type': 11 , 'si': True,  'units': 'C'                , 'function': self.__get_ondie_temperature},
                    'voltage_real_part'         :{'fmt': 'ext. voltage  : {:.2f}'                           , 'type': 13 , 'si': True,  'units': 'V'                , 'function': self.__get_ext_voltage},
                    'voltage_imag_part'         :{'fmt': '{}'                                               , 'type': 14 , 'si': True,  'units': 'V'                , 'function': self.__get_default},
                    'current_real_part'         :{'fmt': 'ext. current  : {:.2f}'                           , 'type': 15 , 'si': True,  'units': 'A'                , 'function': self.__get_ext_current},
                    'current_imag_part'         :{'fmt': '{}'                                               , 'type': 16 , 'si': True,  'units': 'A'                , 'function': self.__get_default},

                    'charge'                    :{'fmt': '{}'                                               , 'type': 19 , 'si': True,  'units': 'C'                , 'function': self.__get_charge},
                    'temperature'               :{'fmt': 'temperature   : {:.2f}'                           , 'type': 20 , 'si': False, 'units': 'C'                , 'function': self.__get_external_temperature},
                    'humidity'                  :{'fmt': 'humidity      : {:.2f}'                           , 'type': 21 , 'si': False, 'units': 'RH'               , 'function': self.__get_external_humidity},
                    'pressure'                  :{'fmt': '{}'                                               , 'type': 22 , 'si': False, 'units': 'bar'              , 'function': self.__get_default},
                    'acceleration_x'            :{'fmt': 'acc. x-axis   : {:.2f}'                           , 'type': 23 , 'si': True,  'units': 'g'                , 'function': self.__get_acceleration},
                    'acceleration_y'            :{'fmt': 'acc. y-axis   : {:.2f}'                           , 'type': 24 , 'si': True,  'units': 'g'                , 'function': self.__get_acceleration},
                    'acceleration_z'            :{'fmt': 'acc. z-axis   : {:.2f}'                           , 'type': 25 , 'si': True,  'units': 'g'                , 'function': self.__get_acceleration},
                    'switch_interrupt'          :{'fmt': 'switch        : {}, {}'                           , 'type': 26 , 'si': False, 'units': ['pin','value']    , 'function': self.__get_switch_value},
                    'audio_average'             :{'fmt': 'audio avg     : {:.2f}'                           , 'type': 27 , 'si': False, 'units': 'count'            , 'function': self.__get_default},
                    'audio_max'                 :{'fmt': 'audio max     : {:.2f}'                           , 'type': 28 , 'si': False, 'units': 'count'            , 'function': self.__get_default},
                    'audio_spl'                 :{'fmt': 'audio spl     : {:.2f}'                           , 'type': 29 , 'si': False, 'units': 'dB'               , 'function': self.__get_default},
                    'ambient_light_visible'     :{'fmt': 'ambient light : {:2f}'                            , 'type': 30 , 'si': False, 'units': 'lux'              , 'function': self.__get_ambient_light},
                    'ambient_light_ir'          :{'fmt': 'ambient ir    : {:2f}'                            , 'type': 31 , 'si': False, 'units': 'lux'              , 'function': self.__get_default},
                    'ambient_light_uv'          :{'fmt': 'uv index      : {:d}'                             , 'type': 32 , 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'co2_level'                 :{'fmt': 'co2 level     : {:d}'                             , 'type': 33 , 'si': False, 'units': 'g'                , 'function': self.__get_default},
                    'distance'                  :{'fmt': 'distance      : {:d}'                             , 'type': 34 , 'si': False, 'units': 'mm'               , 'function': self.__get_distance},
                    'sample_rate'               :{'fmt': 'sample rate   : {:2d}'                            , 'type': 35 , 'si': False, 'units': 'msec'             , 'function': self.__get_default},

                    'magnetometer'              :{'fmt': 'magnetometer  : {:2d}'                            , 'type': 40 , 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'fft_data'                  :{'fmt': 'fft_data      : {:2d}'                            , 'type': 41 , 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'gpio_value'                :{'fmt': 'gpio value    : {:2d}'                            , 'type': 42 , 'si': False, 'units': ''                 , 'function': self.__get_gpio_value},
                    'voc_iaq'                   :{'fmt': 'iaq           : {:2d}, {:d}'                      , 'type': 43 , 'si': False, 'units': ['index', 'state'] , 'function': self.__get_voc_iaq},
                    'voc_temperature'           :{'fmt': 'temperature   : {:2f}'                            , 'type': 44 , 'si': False, 'units': 'C'                , 'function': self.__get_voc_temperature},
                    'voc_humidity'              :{'fmt': 'humidity      : {:2f}'                            , 'type': 45 , 'si': False, 'units': 'RH%'              , 'function': self.__get_voc_humidity},                                        
                    'voc_pressure'              :{'fmt': 'pressure      : {:2f}'                            , 'type': 46 , 'si': False, 'units': 'pA'               , 'function': self.__get_voc_pressure},
                    'voc_ambient_light'         :{'fmt': 'ambient light : {:2f}'                            , 'type': 47 , 'si': False, 'units': 'lux'              , 'function': self.__get_voc_ambient_light},
                    'voc_sound_level'           :{'fmt': 'sound level   : {:2f}'                            , 'type': 48 , 'si': False, 'units': 'dbSpl'            , 'function': self.__get_voc_sound_level},
                    'tof_distance'              :{'fmt': 'distance      : {:2d}, {:d}'                      , 'type': 49 , 'si': False, 'units': ['mm', 'state']    , 'function': self.__get_tof_distance},   
                    'accelerometer_status'      :{'fmt': 'acc. status   : {:2d}'                            , 'type': 50 , 'si': False, 'units': 'state'            , 'function': self.__get_default},                    
                    'gps'                       :{'fmt': 'gps           : {:2d}'                            , 'type': 51 , 'si': False, 'units': 'state'            , 'function': self.__get_default},                    
                    'voltage'                   :{'fmt': 'voltage       : {:.2f}'                           , 'type': 52 , 'si': False, 'units': 'V'                , 'function': self.__get_terminal_voltage},
                    'voltage_diff'              :{'fmt': 'voltage diff  : {:.2f}'                           , 'type': 53 , 'si': False, 'units': 'V'                , 'function': self.__get_terminal_voltage_diff},
                    'voltage_ref'               :{'fmt': 'voltage vref  : {:.2f}'                           , 'type': 54 , 'si': False, 'units': 'V'                , 'function': self.__get_terminal_voltage},

                    'advertisement'             :{'fmt': 'advertisement : {:d}'                             , 'type': 100, 'si': False, 'units': ''                 , 'function': self.__get_default},

                    'stream_start'              :{'fmt': 'stream start  : {:d}'                             , 'type': 121, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'stream_stop'               :{'fmt': 'stream stop   : {:d}'                             , 'type': 122, 'si': False, 'units': ''                 , 'function': self.__get_default},

                    'value_raw'                 :{'fmt': 'raw value     : {:d}'                             , 'type': 123, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'app_sw_ver'                :{'fmt': 'sw ver        : {:d}.{:d}.{:d}'                   , 'type': 124, 'si': False, 'units': ''                 , 'function': self.__get_sw_version},
                    'driver_resp'               :{'fmt': 'drv response  : {:d}'                             , 'type': 125, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'packet_ack'                :{'fmt': 'ack packet id : {:d}'                             , 'type': 126, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'error_code'                :{'fmt': 'error code    : {:d}'                             , 'type': 127, 'si': False, 'units': ''                 , 'function': self.__get_error_code},
                    'crc_code'                  :{'fmt': 'crc 16        : 0x{:x}'                           , 'type': 128, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'shutdown'                  :{'fmt': 'shutdown      : {:d}'                             , 'type': 129, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'variable_length'           :{'fmt': 'varlen        : {:d}'                             , 'type': 130, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'device_id'                 :{'fmt': 'device id     : {:d}'                             , 'type': 131, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'device_pin'                :{'fmt': 'device pin    : {:d}'                             , 'type': 132, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'rssi_level'                :{'fmt': 'rssi level    : {:d}'                             , 'type': 133, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'cell_id'                   :{'fmt': 'cell id       : {:d}'                             , 'type': 134, 'si': False, 'units': ''                 , 'function': self.__get_default},
                    'config_ver'                :{'fmt': 'config ver    : {:d}'                             , 'type': 135, 'si': False, 'units': ''                 , 'function': self.__get_default}
                }

        self.sensors = [
                    'SENSOR_NO_SENSOR',             #0
                    'SENSOR_SI7050_TEMP',           #1
                    'SENSOR_SI7020_HUMIDITY',       #2
                    'SENSOR_SWITCH',                #3
                    'SENSOR_INTERNAL_ADC',          #4
                    'SENSOR_LTC1864L_ADC',          #5
                    'SENSOR_420MA_LOOP',            #6
                    'SENSOR_UART',                  #7
                    'SENSOR_ACCELEROMETER',         #8
                    'SENSOR_DIGITAL_MIC',           #9
                    'SENSOR_AMBIENT_LIGHT',         #10
                    'SENSOR_CO2_MODULE',            #11
                    'SENSOR_CUSTOM_1',              #12
                    'SENSOR_CUSTOM_2',              #13
                    'SENSOR_CUSTOM_3',              #14
                    'SENSOR_CUSTOM_4',              #15
                    'SENSOR_DEBUG',                 #16
                    'SENSOR_ENVIRONMENTAL',         #17
                    'SENSOR_GPS',                   #18
                    'SENSOR_TERMINAL',              #19
                    'SENSOR_TOF',                   #20
                    'SENSOR_PIR',                   #21
                    'SENSOR_CAPA',                  #22
                    'SENSOR_SONAR'                  #23
        ]

        self.errors = [
                'No Error',
                'Generic Error',
                'No Resources',
                'Invalid value',
                'Timeout',
                'Object not found',
                'Invalid state',
                'Hardware error',
                'Device busy',
                'Corrupted resource',
                'Resource in use',
                'Comparison error',
                'Readonly resource',
                'Flash erase',
                'Read error',
                'Write error',
                'Resource already exists',
                'Not supported',
                'Invalid size',
                'Invalid type',
                'Unknown parameter',
                'Access denied',
                'Low voltage',
        ]

    def __str__ (self):
        msg  = ''
        if self.detail:
            msg += '+--+ id              : {:03d} \r\n'.format(self.id)
            msg += '+--+ request id      : {:03d} \r\n'.format(self.requestId)
            msg += '+--+ size            : {:03d} bytes \r\n'.format(self.size)
            
            meas = 0
            data = 0
            typ  = 0
            processed = False
            while not processed:
                (typ, data) = self.__get_meas (meas)
                msg += self.__get_str (typ, data)
                msg += '\r\n'
                if (meas + 1) > (self.meas - 1):
                    processed = True
                else:
                    meas += 1
            msg += '+--+ eop'
        else:
            msg += time.strftime(self.timefmt) + ', '
            msg += 'mac: ' + self.get_mac () + ', '
            msg += 'index: {:03d}, '.format(self.id)
            msg += 'measurements: {:02d}'.format(self.meas) + ', '
            msg += 'size: {} bytes'.format(len(self.pck['payload']))
        return msg

    def set (self, param, value):
        """
        Set parameters for the class, by parameter name
        'detail'    -   print detailed information on call to 
                        .__str__() true/false
        'prefix'    -   add si-prefix to data on 
                        call to .__str__() true/false
        'fullmac'   -   print full or reduced mac addres? 
                        true or false
        'timefmt'   -   format string for timing, default set to
                        '%H:%M:%S'
        """
        boolean_true = ['True', 'true', True]
        boolean_false = ['False', 'false', False]
        if   param == 'detail' and value in boolean_true:
            self.detail = True
        elif param == 'detail' and value in boolean_false:
            self.detail = False
        elif param == 'prefix' and value in boolean_true:
            self.prefix = True
        elif param == 'prefix' and value in boolean_false:
            self.prefix = False
        elif param == 'fullmac' and value in boolean_true:
            self.fullmac = True
        elif param == 'fullmac' and value in boolean_false:
            self.fullmac = False
        elif param == 'timefmt' and type(value) == type(''):
            self.timefmt = value
        else:
            pass

    def add (self, string):
        """
        @brief              Adds packet for processing 
        @param  payload     Expects string of bytes.
                            For example: .add ("fa0101000301100002012a000000002a00000000ced399")
        @retval             None
        """
        array = list()
        for a in range(0, len(string), 2):
            elem = ''.join([string[a], string[a+1]])
            array.append(int(elem,16))

        self.pck        = list (array)
        self.id         = self.pck[PACKET_INDEX]
        self.requestId  = self.pck[PACKET_REQUESTID]
        self.meas       = self.pck[PACKET_MEAS] 
        self.size       = len(self.pck)

    def get_id (self):
    	"""
    	Returns id for the current packet
    	"""
    	return self.id


    def export (self):
        export = {
            'sensors'   : list(),
            'time'      : dict(),
            'packetId'  : self.id,
            'requestId' : self.requestId
        }

        _sensor = {
            'slot'          : DEFAULT_SLOT,
            'sensorType'    : DEFAULT_SENSOR_TYPE,
            'index'         : 0,
            'measurements'  : list()
        }
        meas = 0     # current measurement being processed
        data = 0     # payload
        typ  = 0     # type of payload
        done = False
        # check if packet contains driver type payload
        (typ, data) = self.__get_meas(meas)
        if typ != DRIVER_TYPE:
            # create fake slot
            val = dict(_sensor)
        new = False
        while not done:
            (typ, data) = self.__get_meas (meas)
            if typ == DRIVER_TYPE:
                # append slot to export previous result
                if new:
                    export['sensors'].append (val)
                    new = False
                # start new slot
                val = dict (_sensor)
                (self.slot, self.driver, self.index, self.enabled) = self.__get_driver_info(data)
                val['slot'] = self.slot
                val['sensorType'] = self.sensors[self.driver]
                val['index'] = self.index
                val['measurements'] = list()
                new = True
            else:
                val['measurements'].append(self.__get_json(typ, data))

            # increment to next measurement
            if (meas + 1) > self.meas - 1:
                # append last result
                export['sensors'].append(val)
                done = True
            else:
                meas += 1
        return export


    def __get_meas (self, num):
        type_off = PACKET_OFFSET * num + PACKET_HEADER
        data_off = type_off + 1
        data_type = self.pck[type_off]
        data = 0
        for i in range(3, -1, -1):
            data |= self.pck[data_off + (3 - i)] << (i * 8)
        return (data_type, data) 

    def __get_json (self, typ, data):
        """
        Returns json styled dictionary which contains a single 
        measurement
        """
        raw = {
            'key'   : 'n/a',
            'value' : '0',
            'unit'  : 'n/a'
        }
        for k,v in self.types.items():
            if v['type'] == typ:
                raw['key']  = str(k)    
                # cast units to list if not defined
                # as list to avoid having mutable types
                if type(v['units']) == type(list()):           
                    raw['unit'] = v['units']
                else:
                    raw['unit'] = [v['units']]
                raw['value']= self.types[k]['function'](data)
        return raw

    def __get_str (self, typ, data):
        """
        Returns string representation of the measurement.
        """
        si = tuple()
        res = 0
        ok = False
        for k,v in self.types.items():
            if v['type'] == typ:
                if typ == DRIVER_TYPE:
                    msg  = '+--+ '
                else:
                    msg  = '|  +-- '
                # parse multiple arguments, if available
                if self.types[k]['si'] and self.prefix:
                    res = self.types[k]['function'](data)
                    si  = self.__get_si(res)
                    msg += v['fmt'].format(si[0])
                    msg += ' {}{}'.format(si[1], v['units'])
                else:
                    msg += v['fmt'].format(*self.types[k]['function'](data)) 
                    msg += ' '
                    # parse multiple units if necessary
                    if type(v['units']) == type(list()):
                        msg += ', '.join(v['units'])
                    else:
                        msg += v['units']                        
                # set flag that measurment has been found
                ok = True
        if not ok:
            return ''
        return msg

    def __get_time (self, msb, lsb, offset):
        sample_time = (msb << 32) | (lsb << 0)
        time_str = datetime.datetime.fromtimestamp(
          sample_time
          ).strftime(self.timefmt)

        offset_str = '{:.2f}'.format(offset/1.0e6)

        msg = ' {:s} +{:s} sec'
        msg = msg.format(time_str, offset_str)
        return msg      

    def __get_si (self, val):
        incPrefixes = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
        decPrefixes = ['m', 'u', 'n', 'p', 'f', 'a', 'z', 'y']
        num = val[0]

        if num != 0:
            degree = int(math.floor(math.log10(math.fabs(num)) / 3))
        else:
            degree = 0

        prefix = ''

        if degree!=0:
            ds = degree/math.fabs(degree)
            if ds == 1:
                if degree - 1 < len(incPrefixes):
                    prefix = incPrefixes[degree - 1]
                else:
                    prefix = incPrefixes[-1]
                    degree = len(incPrefixes)

            elif ds == -1:
                if -degree - 1 < len(decPrefixes):
                    prefix = decPrefixes[-degree - 1]
                else:
                    prefix = decPrefixes[-1]
                    degree = -len(decPrefixes)

            scaled = float(num * math.pow(1000, -degree))

        else:
            scaled = num

        return (scaled, prefix)

    def __get_sw_version (self, measurement):
        """
        @brief                  Parses application version

        @param  measurement     Measurement containing encoded firmware version

        @retval                 Returns array of numeric measurements
        """        
        major = ( measurement >> 16 ) & int("FF", 16)
        minor = ( measurement >>  8 ) & int("FF", 16)
        patch = ( measurement >>  0 ) & int("FF", 16)
        return [major, minor, patch]

    def __get_driver_info (self, measurement):
        """
        @brief                  Returns driver information state

        @param  measurement     Measurement containing encoded driver info

        @retval                 Returns array of numeric measurements
        """          
        driver  = measurement >> 24
        slot    = (measurement & int('0x00FF0000', 16)) >> 16
        index   = (measurement & int('0x0000FF00', 16)) >> 8
        enabled = (measurement & int('0x000000FF', 16))

        if enabled == 0:
            enabled = False
        else:
            enabled = True

        return [slot, driver, index, enabled]

    def __get_ondie_voltage (self, measurement):
        voltage = (measurement) / 1000.0
        return [voltage]

    def __get_battery_voltage (self, measurement):
        voltage = measurement / 1000000.0
        return [voltage]

    def __get_ondie_temperature (self, measurement):
        num = ctypes.c_int16(measurement)
        temp = (num.value) / 100.0
        return [temp,]

    def __get_distance (self, measurement):
        return [measurement, ]

    def __get_external_temperature (self, measurement):
        temp = (measurement) * 175.72/65536 - 46.85
        return [temp,]

    def __get_external_humidity (self, measurement):
        humid = (measurement) * 125/65536.0 - 6
        return [humid,]

    def __get_switch_value (self, measurement):
        pin   = measurement >> 8
        value = measurement & 255
        return [pin, value]

    def __get_gpio_value (self, measurement):
        return [measurement,]

    def __get_acceleration (self, measurement):
        num = ctypes.c_int16(measurement).value
        acc = (num >> 6) * 0.0039
        return [acc,]

    def __get_charge       (self, measurement):
        print(measurement)
        num = ctypes.c_uint16(measurement).value
        return [num,]                

    def __get_ext_current (self, measurement):
        return [measurement * 0.0000322911,]

    def __get_ext_voltage (self, measurement):
        return [measurement * 0.0484438,]

    def __get_ambient_light (self, measurement):
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)
        exp = measurement >> 12  # get exponent
        man = measurement & 4095 # get mantissa
        lux = 0.01 * (2**exp) * man 
        return [lux,]           

    def __get_error_code (self, measurement):
        error = ctypes.c_int32(measurement).value * (-1)
        return [error, ]

    def __get_default (self, measurement):
        return  [measurement,]

    def __get_voc_iaq (self, measurement):
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)
        iaq_state = ( measurement >> 14 ) & 3
        iaq_index = ( measurement & int('0x3FFF',16) )        
        return [iaq_index, iaq_state]

    def __get_voc_temperature (self, measurement):
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)        
        temp = measurement & int ('0xFFFF', 16)
        temp = temp / 10.0
        return [temp,]

    def __get_voc_humidity (self, measurement):
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)
        humidity = measurement & int ('0xFFFF', 16)
        humidity = measurement / 100.0        
        return [humidity,]

    def __get_voc_pressure (self, measurement):
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)
        pressure = measurement & int ('0xFFFF', 16)
        pressure = pressure * 10.0           
        return [pressure,]             

    def __get_voc_ambient_light (self, measurement):
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)
        exp = measurement >> 12  # get exponent
        man = measurement & 4095 # get mantissa
        lux = 0.01 * (2**exp) * man 
        return [lux,]               

    def __get_voc_sound_level (self, measurement):    
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)
        rf    = 82000.0
        rs    = 1000.0
        vref  = 11.23 # mV/pa (peak)
        vmic  = -((2 ** (-1 - 16) * rs * 3.0 * (2 ** 16 - 2 * measurement )) / rf)
        try:
        	dbspl = 20 * math.log10 ( vmic / vref) + (-42) + 94
        except:
        	dbspl = 0
        return [dbspl,]

    def __get_tof_distance (self, measurement):
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)
        tof_state = (measurement >> 13 ) & 7
        tof_distance = ( measurement & int('0x1FFF',16) )        
        return [tof_distance, tof_state]    

    def __get_terminal_voltage (self, measurement):
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)
        return [measurement * (3.0/(2**16)),]

    def __get_terminal_voltage_diff (self, measurement):
        measurement = ((measurement >> 8)&255) | ((measurement & 255)<<8)
        return [measurement * (3.0/(2**15)),]