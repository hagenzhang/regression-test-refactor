'''testrunner_file.py

Houses classes that represent a XML test sequence and result JSON for/from the UEI TestRunner.

Due to the simplicity of these classes, documentation is minimal. However, if you wish to
add some for the sake of clarity, it wouldn't hurt (TODO)
'''
import os
import json
import xml.etree.ElementTree as et


class UeiResultJSONParser:
    '''A simple class representing a UEI test result json created by the TestRunner'''
    
    def __init__(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError('Could not find {}'.format(filepath))
        
        with open(filepath) as jfile:
            self.data_list: list = json.load(jfile) 


    def test_result_dict(self):
        '''Retrieves the results represented in the JSON as a dictionary.

        This will only provide the most basic information: the name of the test
        as the key, and the result of the test as the value. 

        The possible results are: Pass, Error, Fatal, Skipped
        '''
        test_results_dict = { }

        for result_dict in self.data_list:
            if result_dict['model'] == 'rsinterface.test':
                field_d: dict = result_dict['fields']
                test_name = field_d.get('testName', '')
                if test_name:
                    test_results_dict[test_name] = field_d.get('status', 'Skipped')
        
        return test_results_dict


    def num_tests(self):
        json_dict = self.test_result_dict()
        num_tests = 0
        for val in json_dict.values():
            if val != 'Skipped':
                num_tests = num_tests + 1
        return num_tests

            


class UeiTestXMLParser:
    '''A simple class representing a UEI test sequence XML for the TestRunner'''

    def __init__(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError('Could not find {}'.format(filepath))
        self.tree = et.parse(filepath)
        self.root = self.tree.getroot()
        self.path = filepath

    def num_tests(self):
        '''Returns the number of tests contained in the XML.
        
        Args:
            None
        Returns:
            num_tests (int): number of tests in the XML.
        '''
        count = 0
        for _ in self.root.findall('./test'):
            count = count + 1
        return count
    
    def add_udp_port(self, ssl_port: int=0, ssl_port_async: int=0):
        '''Adds the udpport property to all tests in an XML.

        The default port is defined by DQ_UDP_DAQ_PORT, which is equal to 6334.
        This function will add a property to the tests in the XML with the name
        'udpport', where the integer value represents the port number.
        
        For all tests except for async tests, we use the DQ_UDP_DAQ_PORT_SSL,
        which has the value of 6354.

        For async tests, we use DQ_UDP_DAQ_PORT_SSL_ASYNC, which has a value
        of 6364. We determine async tests based on the test case.

        Note that a custom port number can be specified, but it is not recommended.
        '''
        for elem in self.tree.findall('./test'):
            if 'async' in elem.attrib['testCase']:
                new_elem = et.fromstring('<property name="udpport"><integer>{}</integer></property>'.format(ssl_port_async))
                elem.append(new_elem)
            else:
                new_elem = et.fromstring('<property name="udpport"><integer>{}</integer></property>'.format(ssl_port))
                elem.append(new_elem)
        
    def remove_udp_port(self):
        '''Reverses the actions of add_udp_port.
        
        Removes any test property with the name 'udpport'. This will make all
        of the tests in an XML run on the default DQ_UDP_DAQ_PORT, or port 6334.
        '''
        for parent in self.tree.findall('./test'):
            for prop in parent.findall('property'):
                # if you wanted, you could make a function that removes all properties with a variable name 
                # using this method (or maybe even a specific property from a specific test).
                # however, we don't need that capability, it remains unimplemented for now.
                if prop.attrib['name'] == 'udpport':
                    parent.remove(prop)

    def write_to_file(self, filepath: str):
        '''Writes out the XML to the given filepath'''
        self.tree.write(filepath)

    def get_global_ip(self):
        '''Gets the global IP specified in the sequence attribute'''
        try:
            return self.root.attrib['ipaddress']
        except KeyError:
            print('Error, XML {} does not have the ipaddress field at the root!'.format(self.path))
            raise
