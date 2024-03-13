import unittest
from gradescope_utils.autograder_utils.decorators import weight
from gradescope_utils.autograder_utils.files import check_submitted_files
from rdt_tester import RDTTester
from gbn_host import GBNHost
import random, string
from struct import pack

class TestSlowArrivalNoCorruptionNoLoss(unittest.TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass


    # This function is responsible for computing the Internet Checksum 
    # for a given packed byte array
    # https://stackoverflow.com/questions/3949726/calculate-ip-checksum-in-python
    def compute_checksum(self, packet):
        s = 0x0000

        # If we have an odd number of bytes, pad the packet with 0x0000
        padded_pkt = None
        pkt_size = len(packet)
        if len(packet) % 2 == 1:
            padded_pkt = packet + bytes(1)
        else:
            padded_pkt = packet

        #print("Creating checksum")
        for i in range(0, len(padded_pkt), 2):
            w = padded_pkt[i] << 8 | padded_pkt[i+1]
            #print("+ " + str(w))
            #print("--------")
            s = self.carry_around_add(s,w)
            #print("  " + str(s))

        checksum = ~s & 0xffff
        #print("--------")
        #print("= " + str(checksum))
        return checksum


    def carry_around_add(self, a, b):
        c = a + b
        return (c&0xffff) + (c >> 16)


    # This function is responsible for checking to see if a received
    # packet is valid, or if it has been corrupted
    # Note: This is slightly different from the official algorithm, because 
    #       self.compute_checksum returns the 1's complement of the sum
    #       This means we compare the result against 0x0000, not 0x1111
    def is_packet_valid(self, packet):
        checksum = self.compute_checksum(packet.bytes)
        result = checksum == 0x0000
        return result


    @weight(5)
    def test_uncorrupted_packet(self):
        input_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))

        pkt = pack("!HIHI%is" % len(input_string), 0b10000000, 48, 0, len(input_string), input_string.encode())
        checksum = self.compute_checksum(pkt)
        pkt = pack("!HIHI%is" % len(input_string), 0b10000000, 48, checksum, len(input_string), input_string.encode())

        gbn = GBNHost(None, None, 10, 10)
        corrupt = gbn.is_corrupt(pkt)

        error_string = "Checked to see if packet [128][48][{}][{}][{}] was corrupt. \nExpected False but got True.".format(checksum, len(input_string), input_string)

        self.assertFalse(corrupt, error_string)
        print("Test passed")


    @weight(5)
    def test_corrupted_packet(self):
        input_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))

        pkt = pack("!HIHI%is" % len(input_string), 0b10000000, 48, 0, len(input_string), input_string.encode())
        checksum = self.compute_checksum(pkt)

        altered_input_string = self.corrupt(pkt)

        gbn = GBNHost(None, None, 10, 10)
        corrupt = gbn.is_corrupt(pkt)

        error_string = "Checked to see if packet [128][48][{}][{}][{}] was corrupt. \nExpected True but got False. The original payload was [{}].".format(checksum, len(input_string), altered_input_string, input_string)

        self.assertTrue(corrupt, error_string)
        print("Test passed")
        
    def corrupt(self, pkt):                
        # Flip a random bit
        bytenum = random.randint(0, len(pkt)-1)
        bitnum = random.randint(0, 7)
        values = bytearray(pkt)
        altered_value = values[bytenum]
        bit_mask = 1 << bitnum
        values[bytenum] = altered_value ^ bit_mask
        return bytes(values)