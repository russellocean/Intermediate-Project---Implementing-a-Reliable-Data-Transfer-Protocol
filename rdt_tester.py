import os, json, sys, re
from optparse import OptionParser
from tkinter.tix import DECREASING
from gbn_host import GBNHost
from network_simulator import NetworkSimulator


class RDTTester():
    def __init__(self, RDTImpl):
        self.RDTImpl = RDTImpl

        self.op = OptionParser(
            version="0.1a",
            description="CPSC 3600 IRC Server application")
        self.op.add_option(
            "--num_pkts",
            metavar="X", type="int",
            help="The number of packets to simulate sending")
        self.op.add_option(
            "--timer_interval",
            metavar="X", type="float",
            help="The timer interval")
        self.op.add_option(
            "--loss_prob",
            metavar="X", type="float",
            help="The probability of losing a packet")
        self.op.add_option(
            "--corrupt_prob",
            metavar="X", type="float",
            help="The probability of losing a packet")
        self.op.add_option(
            "--arrival_rate",
            metavar="X", type="float",
            help="The average time between packets arriving from the application layer")
        self.op.add_option(
            "--capture_log",
            action="store_true",
            help="Captures all print output and stores it in a log file")
        self.op.add_option(
            "--seed",
            metavar="X", type="int",
            help="The seed to use for random generation")


    def run_tests(self, tests):
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        if not os.path.exists(os.path.join(__location__, 'Logs')):
            os.makedirs(os.path.join(__location__, 'Logs'))   

        results = []
        for test in tests:
            # Open the test file
            with open(os.path.join(__location__, 'tests', 'test_cases', '%s.cfg' % test), 'r') as fp:
                test_config = json.load(fp)
                
                # Redirect all output to a log file for this test
                #with open(os.path.join(__location__, 'Logs', '%s.log' % test), 'w') as log:
                passed, errors = self.run_test(test, test_config)
                results.append({
                    'test':test, 
                    'passed':passed, 
                    'errors':errors
                })
                #sys.stdout = sys.__stdout__
                if not passed:
                    print("\n%s failed. See the expected and actual state of your code below.\n" % test)
                    print("%s\n" % errors)
        return results

    def run_test(self, test_name, test):
        try:
            # https://stackoverflow.com/questions/16710076/python-split-a-string-respect-and-preserve-quotes
            args = re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', test["options"])

            options, args = self.op.parse_args(args)
            simulator = NetworkSimulator(test_name, options, self.RDTImpl)
            
            #if options.capture_log:
            #    sys.stdout = log

            result = simulator.Simulate()

            return self.check_test_results(test, simulator, result)
            
        except Exception as e:
            return False, e


    def check_test_results(self, test, simulator, result):
        passed = True
        debug_message = ""

        debug_message += "------------------------------------------------------------------------------------------------------------------------\n"
        result, message = self.check_host(test['final_state']['A'], simulator.A)        
        passed = passed and result
        debug_message += message[:-1]

        debug_message += "------------------------------------------------------------------------------------------------------------------------\n"
        result, message = self.check_host(test['final_state']['B'], simulator.B)
        passed = passed and result
        debug_message += message[:-1]        
        
        debug_message += "------------------------------------------------------------------------------------------------------------------------\n"
        result, message = self.check_simulator(test['final_state']['Simulator'], simulator)
        passed = passed and result
        debug_message += message[:-1]
        debug_message += "------------------------------------------------------------------------------------------------------------------------\n"
        
        return passed, debug_message


    def check_host(self, test, host):
        debug_message = ""
        passed = True
        
        result, message = self.print_list_comparison(entity = str(host.entity), 
            expected_list=test['data_sent'], actual_list=host.data_sent,
            expected_message="Expected to send messages ..................",
            actual_message=  "Actually sent messages .....................",
        )
        passed = passed and result
        debug_message += message


        result, message = self.print_list_comparison(entity = str(host.entity), 
            expected_list=test['data_received'], actual_list=host.data_received,
            expected_message="Expected to receive messages ...............",
            actual_message=  "Actually received messages .................",
        )
        passed = passed and result
        debug_message += message

        result, message = self.print_value_comparison(entity = str(host.entity), 
            expected_value=test['window_base'], actual_value=host.window_base,
            expected_message="Expected final window base .................",
            actual_message=  "Actual final window base ...................",
        )
        passed = passed and result
        debug_message += message
        
        result, message = self.print_value_comparison(entity = str(host.entity), 
            expected_value=test['num_data_sent'], actual_value=host.num_data_sent,
            expected_message="Expected number of data packets sent .......",
            actual_message=  "Actual number of data packets sent .........",
        )
        passed = passed and result
        debug_message += message
        
        result, message = self.print_value_comparison(entity = str(host.entity), 
            expected_value=test['num_ack_sent'], actual_value=host.num_ack_sent,
            expected_message="Expected number of ACK packets sent ........",
            actual_message=  "Actual number of ACK packets sent ..........",
        )
        passed = passed and result
        debug_message += message

        result, message = self.print_value_comparison(entity = str(host.entity), 
            expected_value=test['num_data_received'], actual_value=host.num_data_received,
            expected_message="Expected number of data packets received ...",
            actual_message=  "Actual number of data packets received .....",
        )
        passed = passed and result
        debug_message += message

        result, message = self.print_value_comparison(entity = str(host.entity), 
            expected_value=test['num_ack_received'], actual_value=host.num_ack_received,
            expected_message="Expected number of ack packets received ....",
            actual_message=  "Actual number of ack packets received ......",
        )
        passed = passed and result
        debug_message += message
        
        return passed, debug_message
    

    def check_simulator(self, test, simulator):
        debug_message = ""
        passed = True
        
        result, message = self.print_value_comparison(entity = "Simulator", 
            expected_value=test['num_events'], actual_value=simulator.num_events,
            expected_message="Expected number of total events ................",
            actual_message=  "Actual number of total events ..................",
        )
        passed = passed and result
        debug_message += message

        result, message = self.print_value_comparison(entity = "Simulator", 
            expected_value=test['nsim'], actual_value=simulator.nsim,
            expected_message="Expected number of packets from layer 5 ........",
            actual_message=  "Actual number of packets from layer 5 ..........",
        )
        passed = passed and result
        debug_message += message

        result, message = self.print_value_comparison(entity = "Simulator", 
            expected_value=test['ntolayer3'], actual_value=simulator.ntolayer3,
            expected_message="Expected number of packets from layer 5 ........",
            actual_message=  "Actual number of packets from layer 5 ..........",
        )
        passed = passed and result
        debug_message += message

        result, message = self.print_value_comparison(entity = "Simulator", 
            expected_value=test['nlost'], actual_value=simulator.nlost,
            expected_message="Expected number of lost packets ................",
            actual_message=  "Actual number of lost packets ..................",
        )
        passed = passed and result
        debug_message += message

        result, message = self.print_value_comparison(entity = "Simulator", 
            expected_value=test['ncorrupt'], actual_value=simulator.ncorrupt,
            expected_message="Expected number of corrupt packets .............",
            actual_message=  "Actual number of corrupt packets ...............",
        )
        passed = passed and result
        debug_message += message
        
        return passed, debug_message


    def print_list_comparison(self, entity, expected_message, actual_message, expected_list, actual_list):
        debug_info = ""

        if len(self.diff(actual_list, expected_list)) > 0 or len(self.diff(expected_list, actual_list)) > 0:
            passed = False
        else:
            passed = True

        expected_string = '"' + '","'.join(expected_list) + '"'
        actual_string = '"' + '","'.join(actual_list) + '"'

        debug_info += f"{str(entity)}: {expected_message} [{expected_string}]\n"
        debug_info += f"{str(entity)}: {actual_message} [{actual_string}]\n"

        return passed, debug_info + "\n"


    
    def print_value_comparison(self, entity, expected_message, actual_message, expected_value, actual_value):
        debug_info = ""

        if expected_value != actual_value:
            passed = False
        else:
            passed = True

        debug_info += f"{str(entity)}: {expected_message} [{expected_value}]\n"
        debug_info += f"{str(entity)}: {actual_message} [{actual_value}]\n"

        return passed, debug_info + "\n"


    def find_problems_with_list(self, entity, propertyname, desired_list, actual_list):
        problems = ""
        if len(desired_list) != len(actual_list):
            problems += "%s: Wrong number of %s (found %i, expected %i)\n" % (entity, propertyname, len(actual_list), len(desired_list))
        
        missing_from_actual = self.diff(actual_list, desired_list)
        if missing_from_actual:
            problems += "%s: Missing from %s: %s\n" % (entity, propertyname, ", ".join(missing_from_actual))

        extra_in_actual = self.diff(desired_list, actual_list)
        if extra_in_actual:
            problems += "%s: Extra in %s: %s\n" % (entity, propertyname, ", ".join(extra_in_actual))

        return problems


    def find_problems_with_value(self, entity, propertyname, desired_value, actual_value):
        if desired_value != actual_value:
            return "%s: Wrong value for %s (found %s, expected %s)\n" % (entity, propertyname, actual_value, desired_value)
        return ""


    # Helper function to find what differences exist in two lists
    def diff(self, list1, list2):
        return (list(set(list1) - set(list2)))

    def union(self, lst1, lst2): 
        final_list = list(set(lst1) | set(lst2)) 
        return final_list

    def intersect(self, lst1, lst2): 
        final_list = list(set(lst1) & set(lst2)) 
        return final_list


if __name__ == "__main__":
    
    tests = {
        "Test1_SlowDataRate_0Loss_0Corruption": 13,
        "Test2_SlowDataRate_25Loss_0Corruption": 6.5,
        "Test3_SlowDataRate_0Loss_25Corruption": 6.5,
        "Test4_SlowDataRate_25Loss_25Corruption": 6.5,
        "Test5_MediumDataRate_0Loss_0Corruption": 4.0625,
        "Test6_MediumDataRate_10Loss_0Corruption": 4.0625,
        "Test7_MediumDataRate_0Loss_10Corruption": 4.0625,
        "Test8_MediumDataRate_10Loss_10Corruption": 4.0625,
        "Test9_FastDataRate_0Loss_0Corruption": 4.0625,
        "Test10_FastDataRate_10Loss_0Corruption": 4.0625,
        "Test11_FastDataRate_0Loss_10Corruption": 4.0625,
        "Test12_FastDataRate_10Loss_10Corruption": 4.0625,
    }

    test_manager = RDTTester(GBNHost)
    score = test_manager.run_tests(tests.keys())
    
    print("\n\nTest Results:")
    for s in score:
        print(f" * {s['test']}: {'.'*(54 - len(s['test']))} {'Passed' if s['passed'] else 'Failed'}")

    max_score = 0
    final_score = 0
    for s in score:
        max_score += tests[s['test']]
        if s['passed']:
            final_score += tests[s['test']]
            
    print(f"\nFinal Score: {final_score} out of {max_score}")