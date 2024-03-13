import unittest
from gradescope_utils.autograder_utils.decorators import weight
from gradescope_utils.autograder_utils.files import check_submitted_files
from rdt_tester import RDTTester
from gbn_host import GBNHost

class TestSlowArrival(unittest.TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    @weight(13)
    def test_slow_arrival_no_corruption_no_loss(self):
        tests = [
            "Test1_SlowDataRate_0Loss_0Corruption"
        ]

        test_manager = RDTTester(GBNHost)
        score = test_manager.run_tests(tests)

        self.assertTrue(score[0]['passed'], score[0]['errors'])
        print('Passed test successfully')


    @weight(6.5)
    def test_slow_arrival_no_corruption_25_loss(self):
        tests = [
            "Test2_SlowDataRate_25Loss_0Corruption"
        ]

        test_manager = RDTTester(GBNHost)
        score = test_manager.run_tests(tests)

        self.assertTrue(score[0]['passed'], score[0]['errors'])
        print('Passed test successfully')


    @weight(6.5)
    def test_slow_arrival_25_corruption_no_loss(self):
        tests = [
            "Test3_SlowDataRate_0Loss_25Corruption"
        ]

        test_manager = RDTTester(GBNHost)
        score = test_manager.run_tests(tests)

        self.assertTrue(score[0]['passed'], score[0]['errors'])
        print('Passed test successfully')


    @weight(6.5)
    def test_slow_arrival_25_corruption_25_loss(self):
        tests = [
            "Test4_SlowDataRate_25Loss_25Corruption"
        ]

        test_manager = RDTTester(GBNHost)
        score = test_manager.run_tests(tests)

        self.assertTrue(score[0]['passed'], score[0]['errors'])
        print('Passed test successfully')
