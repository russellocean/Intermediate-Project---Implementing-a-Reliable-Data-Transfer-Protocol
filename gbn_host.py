from struct import error, pack, unpack

MAX_UNSIGNED_INT = 4294967295


class GBNHost:

    def __init__(self, simulator, entity, timer_interval, window_size):
        """Initializes important values for GBNHost objects

        In addition to storing the passed in values, the values indicated in the initialization transition for the
        GBN Sender and GBN Receiver finite state machines also need to be initialized. This has been done for you.

        Args:
            simulator (NetworkSimulator): contains a reference to the network simulator that will be used to communicate
                with other instances of GBNHost. You'll need to call four methods from the simulator:
                pass_to_application_layer, pass_to_network_layer, start_timer, and stop_timer.
            entity (EventEntity): contains a value representing which entity this is. You'll need this when calling
                any of functions in the simulator (the available functions are specified above).
            timer_interval (float): the amount of time that should pass before a timer expires
            window_size (int): the size of the window being used by this GBNHost
        Returns:
            nothing
        """

        # These variables are relevant to the functionality defined in both the GBN Sender and Receiver FSMs
        self.simulator = simulator
        self.entity = entity
        self.window_size = window_size

        # The variables are relevant to the GBN Sender FSM
        self.timer_interval = timer_interval
        self.window_base = 0
        self.next_seq_num = 0
        self.unacked_buffer = [
            None
        ] * window_size  # Creates a list of length self.window_size filled with None values
        self.app_layer_buffer = []

        # These variables are relevant to the GBN Receiver FSM
        self.expected_seq_num = 0
        self.last_ack_pkt = self.create_ack_pkt(MAX_UNSIGNED_INT)

    def receive_from_application_layer(self, payload):
        """Implements the functionality required to send packets received from simulated applications via the network
            simualtor.

        This function will be called by the NetworkSimualtor when simulated data needs to be sent across the
        network. It should implement all SENDING functionality from the GBN Sender FSM. Refer to the FSM for
        implementation details.

        You'll need to call self.simulator.pass_to_network_layer(), self.simulator.start_timer(), and
        self.simulator.stop_timer() in this function. Make sure you pass self.entity as the first argument when
        calling any of these functions.

        Args:
            payload (string): the payload provided by a simulated application that needs to be sent
        Returns:
            nothing
        """
        pass

    def receive_from_network_layer(self, packet):
        """Implements the functionality required to receive packets received from simulated applications via the
            network simualtor.

        This function will be called by the NetworkSimualtor when simulated packets are ready to be received from
        the network. It should implement all RECEIVING functionality from the GBN Sender and GBN Receiver FSMs.
        Refer to both FSMs for implementation details.

        Note that this is a more complex function to implement than receive_from_application_layer as it will
        involve handling received data packets and acknowledgment packets separately. The logic for handling
        received data packets is detailed in the GBN Receiver FSM and the logic for handling received acknowledgment
        packets is detailed in the GBN Sender FSM.

        You'll need to call self.simulator.pass_to_application_layer() and self.simulator.pass_to_network_layer(),
        in this function. Make sure you pass self.entity as the first argument when calling any of these functions.

        HINT: Remember that your default ACK message has a sequence number that is one less than 0, which turns into
              4294967295 as it's unsigned int. When you check to make sure that the seq_num of an ACK message is
              >= window_base you'll also want to make sure it is not 4294967295 since you won't want to update your
              window_base value from that first default ack.

        Args:
            packet (bytes): the bytes object containing the packet data
        Returns:
            nothing
        """
        pass

    def timer_interrupt(self):
        """Implements the functionality that handles when a timeout occurs for the oldest unacknowledged packet

        This function will be called by the NetworkSimulator when a timeout occurs for the oldest unacknowledged packet
        (i.e. too much time as passed without receiving an acknowledgment for that packet). It should implement the
        appropriate functionality detailed in the GBN Sender FSM.

        You'll need to call self.simulator.start_timer() in this function. Make sure you pass self.entity as the first
        argument when calling this functions.

        Args:
            None
        Returns:
            None
        """
        pass

    def create_data_pkt(self, seq_num, payload):
        """Create a data packet with a given sequence number and variable length payload

        Data packets contain the following fields:
            packet_type (unsigned half): this should always be 0x0 for data packets
            seq_num (unsigned int): this should contain the sequence number for this packet
            checksum (unsigned half): this should contain the checksum for this packet
            payload_length (unsigned int): this should contain the length of the payload
            payload (varchar string): the payload contains a variable length string

        Note: generating a checksum requires a bytes object containing all of the packet's data except for the checksum
              itself. It is recommended to first pack the entire packet with a placeholder value for the checksum
              (i.e. 0), generate the checksum, and to then repack the packet with the correct checksum value.

        Args:
            seq_num (int): the sequence number of this packet
            payload (string): the variable length string that should be included in this packet
        Returns:
            bytes: a bytes object containing the required fields for a data packet
        """
        # Define packet type for data packets
        packet_type = 0x0

        # Initial checksum value set to 0
        checksum_placeholder = 0

        # Calculate payload length
        payload_length = len(payload)

        # Pack the packet with a placeholder for checksum
        packet_without_checksum = pack(
            "!HHIIs",
            packet_type,
            checksum_placeholder,
            seq_num,
            payload_length,
            payload.encode(),
        )

        # Calculate checksum
        checksum = self.create_checksum(packet_without_checksum)

        # Repack the packet with the correct checksum
        packet_with_checksum = pack(
            "!HHIIs", packet_type, checksum, seq_num, payload_length, payload.encode()
        )

        return packet_with_checksum

    def create_ack_pkt(self, seq_num):
        """Create an acknowledgment packet with a given sequence number

        Acknowledgment packets contain the following fields:
            packet_type (unsigned half): this should always be 0x1 for ack packets
            seq_num (unsigned int): this should contain the sequence number of the packet being acknowledged
            checksum (unsigned half): this should contain the checksum for this packet

        Note: generating a checksum requires a bytes object containing all of the packet's data except for the checksum
              itself. It is recommended to first pack the entire packet with a placeholder value for the checksum
              (i.e. 0), generate the checksum, and to then repack the packet with the correct checksum value.

        Args:
            seq_num (int): the sequence number of this packet
            payload (string): the variable length string that should be included in this packet
        Returns:
            bytes: a bytes object containing the required fields for a data packet
        """
        # Define packet type for ACK packets
        packet_type = 0x1

        # Initial checksum value set to 0
        checksum_placeholder = 0

        # Pack the packet with a placeholder for checksum
        packet_without_checksum = pack(
            "!HHI", packet_type, checksum_placeholder, seq_num
        )

        # Calculate checksum
        checksum = self.create_checksum(packet_without_checksum)

        # Repack the packet with the correct checksum
        packet_with_checksum = pack("!HHI", packet_type, checksum, seq_num)

        return packet_with_checksum

    # This function should accept a bytes object and return a checksum for the bytes object.
    def create_checksum(self, packet):
        """Create an Internet checksum for a given bytes object

        This function should return a checksum generated using the Internet checksum algorithm. The value you compute
        should be able to be represented as an unsigned half (i.e. between 0 and 65536). In general, Python stores most
        numbers as ints. You do *not* need to cast your computed checksum to an unsigned half when returning it. This
        will be done when packing the checksum.

        Args:
            packet (bytes): the bytes object that the checksum will be based on
        Returns:
            int: the checksum value
        """
        # Ensure packet length is even by padding with a 0-byte if necessary
        if len(packet) % 2 == 1:
            packet += bytes(1)

        # Initialize sum
        checksum_sum = 0

        # Process each 16-bit segment of the packet
        for i in range(0, len(packet), 2):
            # Combine two bytes to form a 16-bit word
            word = (packet[i] << 8) + packet[i + 1]
            checksum_sum += word
            checksum_sum = (checksum_sum & 0xFFFF) + (checksum_sum >> 16)

        # Perform 1's complement
        checksum = ~checksum_sum & 0xFFFF

        return checksum

    def unpack_pkt(self, packet):
        """Create a dictionary containing the contents of a given packet

        This function should unpack a packet and return the values it contains as a dictionary. Valid dictionary keys
        include: "packet_type", "seq_num", "checksum", "payload_length", and "payload". Only include keys that have
        associated values (i.e. "payload_length" and "payload" are not needed for ack packets). The packet_type value
        should be either 0x0 or 0x1. It should not be represented a bool

        Note: unpacking a packet is generally straightforward, however it is complicated if the payload_length field is
              corrupted. In this case, you may attempt to unpack a payload larger than the actual available data. This
              will result in a struct.error being raised with the message "unpack requires a buffer of ## bytes". THIS
              IS EXPECTED BEHAVIOR WHEN PAYLOAD_LENGTH IS CORRUPTED. It indicates that the packet has been corrupted,
              not that you've done something wrong (unless you're getting this on tests that don't involve corruption).
              If this occurs, treat this packet as a corrupted packet.

              I recommend wrapping calls to unpack_pkt in a try... except... block that will catch the struct.error
              exception when it is raised. If this exception is raised, then treat the packet as if it is corrupted in
              the function calling unpack_pkt().

        Args:
            packet (bytes): the bytes object containing the packet data
        Returns:
            dictionary: a dictionary containing the different values stored in the packet
        """

        try:
            # Unpack the first 8 bytes to get packet_type, seq_num, and checksum
            packet_type, seq_num, checksum = unpack("!HHI", packet[:8])
            # Check if the packet is corrupted using the is_corrupt function
            if self.is_corrupt(packet):
                raise ValueError("Packet is corrupted")

            # Initialize the dictionary with known values
            unpacked_data = {
                "packet_type": packet_type,
                "seq_num": seq_num,
                "checksum": checksum,
            }
            # Check if there's more data for payload_length and payload
            if len(packet) > 8:
                # Attempt to unpack payload_length
                payload_length = unpack("!I", packet[8:12])[0]
                # Add payload_length to the dictionary
                unpacked_data["payload_length"] = payload_length
                # Extract payload using the payload_length
                payload = packet[12 : 12 + payload_length]
                # Add payload to the dictionary if it exists
                unpacked_data["payload"] = payload
            return unpacked_data
        except error as e:
            # If an error occurs, it's likely due to a corrupted packet
            raise ValueError("Packet is corrupted") from e

    # This function should check to determine if a given packet is corrupt. The packet parameter accepted
    # by this function should contain a bytes object
    def is_corrupt(self, packet):
        """Determine whether a packet has been corrupted based on the included checksum

        This function should use the included Internet checksum to determine whether this packet has been corrupted.

        Args:
            packet (bytes): a bytes object containing a packet's data
        Returns:
            bool: whether or not the packet data has been corrupted
        """
        # Unpack the packet to extract the packet type, checksum, sequence number, and payload (if applicable)
        try:
            # Assuming the packet format: packet type (2 bytes), checksum (2 bytes), sequence number (4 bytes),
            # followed by optional payload length (4 bytes) and payload.
            # Adjust the unpacking format string as per your packet structure.
            packet_type, included_checksum, seq_num = unpack("!HHI", packet[:8])
            payload = packet[8:] if len(packet) > 8 else b""

            # Recreate the packet without the included checksum (substitute with 0) for checksum calculation
            packet_without_checksum = pack("!HHI", packet_type, 0, seq_num) + payload

            # Recalculate the checksum for the packet without the included checksum
            recalculated_checksum = self.create_checksum(packet_without_checksum)

            # Compare the included checksum with the recalculated checksum
            return included_checksum != recalculated_checksum
        except error:
            # If unpacking fails due to a corrupted packet structure, consider the packet corrupt
            return True
