import unittest
from gradescope_utils.autograder_utils.decorators import weight
from gradescope_utils.autograder_utils.files import check_submitted_files
from rdt_tester import RDTTester
from gbn_host import GBNHost

class TestMediumArrival(unittest.TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    @weight(4.0625)
    def test_medium_arrival_no_corruption_no_loss(self):
        tests = [
            "Test5_MediumDataRate_0Loss_0Corruption"
        ]

        test_manager = RDTTester(GBNHost)
        score = test_manager.run_tests(tests)

        self.assertTrue(score[0]['passed'], score[0]['errors'])
        print('Passed test successfully')


    @weight(4.0625)
    def test_medium_arrival_no_corruption_10_loss(self):
        tests = [
            "Test6_MediumDataRate_10Loss_0Corruption"
        ]

        test_manager = RDTTester(GBNHost)
        score = test_manager.run_tests(tests)

        self.assertTrue(score[0]['passed'], score[0]['errors'])
        print('Passed test successfully')


    @weight(4.0625)
    def test_medium_arrival_10_corruption_no_loss(self):
        tests = [
            "Test7_MediumDataRate_0Loss_10Corruption"
        ]

        test_manager = RDTTester(GBNHost)
        score = test_manager.run_tests(tests)

        self.assertTrue(score[0]['passed'], score[0]['errors'])
        print('Passed test successfully')


    @weight(4.0625)
    def test_medium_arrival_10_corruption_10_loss(self):
        tests = [
            "Test8_MediumDataRate_10Loss_10Corruption"
        ]

        test_manager = RDTTester(GBNHost)
        score = test_manager.run_tests(tests)

        self.assertTrue(score[0]['passed'], score[0]['errors'])
        print('Passed test successfully')
