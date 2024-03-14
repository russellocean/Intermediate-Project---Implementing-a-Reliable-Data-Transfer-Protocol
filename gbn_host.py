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
        if len(self.app_layer_buffer) < self.window_size:
            self.app_layer_buffer.append(payload)

        while (
            self.next_seq_num < self.window_base + self.window_size
            and self.app_layer_buffer
        ):
            pkt_payload = self.app_layer_buffer.pop(0)
            pkt = self.create_data_pkt(self.next_seq_num, pkt_payload)
            self.unacked_buffer[self.next_seq_num % self.window_size] = pkt

            print(
                f"Sending packet {self.next_seq_num} with checksum {self.unpack_pkt(pkt)['checksum']} to network layer. Window base: {self.window_base}, next_seq_num: {self.next_seq_num}. Payload: {pkt_payload}"
            )
            self.simulator.pass_to_network_layer(self.entity, pkt)
            if self.window_base == self.next_seq_num:
                self.simulator.start_timer(self.entity, self.timer_interval)
            self.next_seq_num += 1

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
            if not self.is_corrupt(packet) and seq_num != MAX_UNSIGNED_INT:
                if self.window_base <= seq_num < self.next_seq_num:
                    self.window_base = seq_num + 1
                    if self.window_base == self.next_seq_num:
                        self.simulator.stop_timer(self.entity)
                    else:
                        self.simulator.start_timer(self.entity, self.timer_interval)
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
        self.simulator.start_timer(self.entity, self.timer_interval)
        for i in range(self.window_base, self.next_seq_num):
            print(f"Resending packet {i % self.window_size}")
            if self.unacked_buffer[i % self.window_size]:
                print(f"Resending packet {i % self.window_size}")
                self.simulator.pass_to_network_layer(
                    self.entity, self.unacked_buffer[i % self.window_size]
                )

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
        packet_type = 0x0
        payload_length = len(payload)
        checksum = 0
        # Packet format before checksum: packet_type, seq_num, checksum (placeholder), payload_length, payload
        pkt_without_checksum = pack(
            "!HIHI{}s".format(payload_length),
            packet_type,
            seq_num,
            checksum,
            payload_length,
            payload.encode(),
        )
        checksum = self.create_checksum(pkt_without_checksum)
        return pack(
            "!HIHI{}s".format(payload_length),
            packet_type,
            seq_num,
            checksum,
            payload_length,
            payload.encode(),
        )

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
        packet_type = 0x1
        checksum = 0
        # Packet format before checksum: packet_type, seq_num, checksum (placeholder)
        pkt_without_checksum = pack("!HIH", packet_type, seq_num, checksum)
        checksum = self.create_checksum(pkt_without_checksum)
        return pack("!HIH", packet_type, seq_num, checksum)

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
        # Summation of all 16-bit words in the packet
        sum = 0
        for i in range(0, len(packet), 2):
            if i + 1 < len(packet):
                word = (packet[i] << 8) + packet[i + 1]
            else:
                word = packet[i] << 8
            sum = sum + word

        # Add carry to the sum if any
        while (sum >> 16) > 0:
            sum = (sum & 0xFFFF) + (sum >> 16)

        # One's complement of the sum
        checksum = ~sum & 0xFFFF
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
            # Check minimum length for type and sequence number and checksum
            if len(packet) < 6:
                print("Packet is too short for type, sequence number, and checksum")
                return None  # Not enough data for any packet

            # Unpack common header parts
            packet_type, seq_num, checksum = unpack("!HIH", packet[:8])

            unpacked_data = {
                "packet_type": packet_type,
                "seq_num": seq_num,
                "checksum": checksum,
            }

            # For ACK packets, this is all we need
            if packet_type == 0x1:
                print("ACK packet")
                return unpacked_data

            # Ensure there's enough remaining packet for payload_length
            if len(packet) < 12:
                print("Packet is too short for payload length")
                return None  # Not enough data for a data packet

            # Extract payload_length for data packets
            (payload_length,) = unpack("!I", packet[8:12])
            if len(packet) < 12 + payload_length:
                print("Packet is too short for its claimed payload length")
                print(f"Packet length: {len(packet)}, payload length: {payload_length}")
                # Packet is too short for its claimed payload length
                return None

            # Extract the payload, if any
            payload_format = f"!{payload_length}s"
            (payload,) = unpack(payload_format, packet[12 : 12 + payload_length])
            unpacked_data["payload_length"] = payload_length
            unpacked_data["payload"] = payload

            return unpacked_data
        except error as e:
            # Log or handle the specific struct.error if needed
            print(f"Error unpacking packet: {e}")
            return None

    def is_corrupt(self, packet):
        """Determine whether a packet has been corrupted based on the included checksum and handle payload length corruption.

        This function should use the included Internet checksum to determine whether this packet has been corrupted.
        It also handles cases where the payload length might be corrupted, leading to exceptions when unpacking.

        Args:
            packet (bytes): a bytes object containing a packet's data
        Returns:
            bool: whether or not the packet data has been corrupted
        """
        try:
            # Attempt to unpack the packet type, sequence number, and checksum
            packet_type, seq_num, original_checksum = unpack("!HIH", packet[:8])

            # If the packet is an ACK, it has no payload length or payload, so only the checksum is checked
            if packet_type == 0x1:
                packet_without_checksum = pack(
                    "!HIH",
                    packet_type,
                    seq_num,
                    0,
                )
                recalculated_checksum = self.create_checksum(packet_without_checksum)

                is_corrupt = recalculated_checksum != original_checksum

            else:
                # Attempt to unpack the payload length, if it fails, the packet is corrupt
                payload_length = unpack("!I", packet[8:12])[0]
                payload = packet[
                    12 : 12 + payload_length
                ]  # This might raise an exception if payload_length is corrupted

                # Reconstruct packet without checksum for validation
                packet_without_checksum = pack(
                    "!HIHI{}s".format(len(payload)),
                    packet_type,
                    seq_num,
                    0,
                    payload_length,
                    payload,
                )

                # Recalculate checksum
                recalculated_checksum = self.create_checksum(packet_without_checksum)

                # Compare recalculated checksum with the original
                is_corrupt = recalculated_checksum != original_checksum

        except error as e:
            # If an exception is caught, it's likely due to a corrupted packet length
            print(f"Exception caught indicating potential corruption: {str(e)}")
            is_corrupt = True

        print(f"Packet is corrupt: {is_corrupt}")
        return is_corrupt
