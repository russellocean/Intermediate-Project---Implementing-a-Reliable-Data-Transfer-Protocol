# from network_simulator import NetworkSimulator, EventEntity
# from enum import Enum
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
        # Check if the window is not full
        if self.next_seq_num < self.window_base + self.window_size:
            # Create a packet with the current sequence number and payload
            packet = self.create_data_pkt(self.next_seq_num, payload)

            # Append the packet to the unacknowledged buffer
            self.unacked_buffer[self.next_seq_num % self.window_size] = packet
            # Pass the packet to the network layer
            self.simulator.pass_to_network_layer(
                self.entity,
                packet,
            )
            # If this is the first packet in the window, start the timer
            if self.window_base == self.next_seq_num:
                self.simulator.start_timer(self.entity, self.timer_interval)
            # Increment the next sequence number
            self.next_seq_num += 1
        else:
            # If the window is full, buffer the application data
            self.app_layer_buffer.append(payload)

    def receive_from_network_layer(self, packet):
        """Implements the functionality required to receive packets received from simulated applications via the
            network simualtor.

        This function will be called by the NetworkSimualtor when simulated packets are ready to be received from
        the network. It should implement all RECEIVING functionality from the GBN Sender and GBN Receiver FSMs.
        Refer to both FSMs for implementation details.

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

        print("Received packet: ", packet)

        # Unpack the packet and extract if it is an ACK or data packet
        packet_type, seq_num, checksum = unpack("!HIH", packet[:8])

        # Determine if the packet is an ACK or a data packet
        is_ack = packet_type == 0x1

        # Handle ACK packets
        if is_ack:
            # Check if the packet is not corrupted and not the default ACK packet
            if not self.is_corrupt(packet) and seq_num != MAX_UNSIGNED_INT:
                # Check if the ACK is within the window
                if seq_num >= self.window_base and seq_num < self.next_seq_num:
                    # Slide the window and manage the timer
                    self.window_base = seq_num + 1
                    self.simulator.stop_timer(self.entity)
                    if self.window_base != self.next_seq_num:
                        self.simulator.start_timer(self.entity, self.timer_interval)
                    # Process any buffered application layer data if the window has space
                    self.process_app_layer_buffer()

        # Handle data packets
        else:
            if not self.is_corrupt(packet) and seq_num == self.expected_seq_num:
                # Process the packet
                try:
                    data = self.unpack_pkt(packet)["payload"].decode()
                except Exception:
                    # If unpacking fails, treat as a corrupt packet
                    self.simulator.pass_to_network_layer(self.entity, self.last_ack_pkt)
                else:
                    # Pass the data to the application layer and send an ACK
                    self.simulator.pass_to_application_layer(self.entity, data)
                    self.last_ack_pkt = self.create_ack_pkt(self.expected_seq_num)
                    self.simulator.pass_to_network_layer(self.entity, self.last_ack_pkt)
                    self.expected_seq_num += 1
            else:
                # If the packet is not expected or is corrupt, resend the last ACK
                self.simulator.pass_to_network_layer(self.entity, self.last_ack_pkt)

    def process_app_layer_buffer(self):
        """Processes buffered application layer data if the window has space."""
        while (
            len(self.app_layer_buffer) > 0
            and self.next_seq_num < self.window_base + self.window_size
        ):
            payload = self.app_layer_buffer.pop(0)
            self.receive_from_application_layer(payload)

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
        packets_to_resend = False
        for a in range(self.window_base, self.next_seq_num):
            packet = self.unacked_buffer[a % self.window_size]
            if packet:  # Ensure the packet exists before attempting to resend
                self.simulator.pass_to_network_layer(self.entity, packet)
                print(f"Resending packet {a}")
                packets_to_resend = True

        if packets_to_resend:
            # Only restart the timer if there are packets to resend
            self.simulator.start_timer(self.entity, self.timer_interval)
        else:
            print("No packets to resend")

    def create_data_pkt(self, seq_num, payload):
        """Create a data packet with a given sequence number and variable length payload

        Data packets contain the following fields:
            packet_type (unsigned half): this should always be 0x0 for data packets (2 bytes)
            seq_num (unsigned int): this should contain the sequence number for this packet (4 bytes)
            checksum (unsigned half): this should contain the checksum for this packet (2 bytes)
            payload_length (unsigned int): this should contain the length of the payload (4 bytes)
            payload (varchar string): the payload contains a variable length string (variable bytes)

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

        # Calculate payload length
        payload_length = len(payload)

        # Pack the packet without a checksum first
        packet_format = "!HIHI{}s".format(
            payload_length
        )  # Format string without placeholder for checksum
        packet_without_checksum = pack(
            packet_format,
            packet_type,
            seq_num,
            0,  # Placeholder for checksum, actual value to be calculated later
            payload_length,
            payload.encode(),
        )

        # Calculate checksum
        checksum = self.create_checksum(packet_without_checksum)

        # Repack the packet with the correct checksum
        packet_format_with_checksum = "!HIHI{}s".format(
            payload_length
        )  # Adjust format string to include checksum
        packet_with_correct_checksum = pack(
            packet_format_with_checksum,
            packet_type,
            seq_num,
            checksum,  # Correct checksum
            payload_length,
            payload.encode(),
        )

        return packet_with_correct_checksum

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
        packet_type = 0x1  # Define packet type for acknowledgment packets

        # Initial packet packing without checksum
        packet_format = "!HIH"  # Format string including placeholder for checksum
        packet_without_checksum = pack(
            packet_format,
            packet_type,
            seq_num,
            0,  # Placeholder for checksum, actual value to be calculated later
        )

        # Checksum calculation
        checksum = self.create_checksum(packet_without_checksum)

        # Repack the packet with the correct checksum
        packet_with_correct_checksum = pack(
            packet_format,
            packet_type,
            seq_num,
            checksum,  # Correct checksum
        )

        return packet_with_correct_checksum

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
        sum = 0
        for i in range(0, len(packet), 2):
            if i + 1 < len(packet):
                sum += (packet[i] << 8) + packet[i + 1]
            else:
                sum += packet[i] << 8
            sum = (sum & 0xFFFF) + (sum >> 16)
        return ~sum & 0xFFFF

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
            # Extract the packet type and checksum from the beginning of the packet
            packet_type, seq_num, checksum = unpack("!HIH", packet[:8])

            # Initialize the dictionary with known values
            unpacked_data = {
                "packet_type": packet_type,
                "seq_num": seq_num,
                "checksum": checksum,
            }

            # For ACK packets, only packet_type and checksum are needed
            if packet_type == 0x1:  # ACK packet
                return unpacked_data

            # For data packets, additional fields are extracted
            payload_length = unpack("!I", packet[8:12])[0]

            # If there's payload data, extract it
            if payload_length > 0:
                payload_format = f"!{payload_length}s"
                payload = unpack(payload_format, packet[12 : 12 + payload_length])[0]
                unpacked_data["payload_length"] = payload_length
                unpacked_data["payload"] = payload

            return unpacked_data
        except error:
            # If an error occurs, it's likely due to a corrupted packet
            return None

    def is_corrupt(self, packet):
        """Determine whether a packet has been corrupted based on the included checksum

        This function should use the included Internet checksum to determine whether this packet has been corrupted.

        Args:
            packet (bytes): a bytes object containing a packet's data
        Returns:
            bool: whether or not the packet data has been corrupted
        """

        # Correctly reconstruct packet without checksum for validation
        packet_type, seq_num, original_checksum = unpack("!HIH", packet[:8])
        payload = packet[8:]
        packet_without_checksum = pack(
            "!HIH{}s".format(len(payload)),
            packet_type,
            seq_num,
            0,
            payload,
        )

        # Recalculate checksum
        recalculated_checksum = self.create_checksum(packet_without_checksum)

        print(f"Packet is corrupt: {recalculated_checksum != original_checksum}")

        # Compare recalculated checksum with the original
        return recalculated_checksum != original_checksum
