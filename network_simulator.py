from multiprocessing import Event
import sys, copy, random, logging, struct
from enum import Enum, IntEnum
import json

class NetworkSimulator():

    # *********************** Simulator routines ***********************
    # ************ DO NOT CALL ANY ROUTINES IN THIS SECTION ************
    # *********** ROUTINES FOR STUDENT USE CAN BE FOUND BELOW **********
    def __init__(self, test_name, options, RDTHost):
        self.continue_simulation = True
        self.event_list = []

        # Configuration for the packet simulation
        self.max_events = options.num_pkts              # number of msgs to generate, then stop
        self.timer_interval = options.timer_interval     
        self.lossprob = options.loss_prob               # probability that a packet is dropped
        self.corruptprob = options.corrupt_prob         # probability that one bit is packet is flipped
        self.arrival_rate = options.arrival_rate        # arrival rate of messages from layer 5

        # Record statistics of what has happened to packets in our simulated network
        self.num_events = 0
        self.time = 0.000       #
        self.nsim = 0           # number of messages from 5 to 4 so far
        self.ntolayer3 = 0      # number sent into layer 3
        self.nlost = 0          # number lost in media
        self.ncorrupt = 0       # number corrupted by media
        
        # If we specify a seed, initialize random with it
        if options.seed:
            random.seed(options.seed)

        # Create the two hosts we will be simulating
        self.A = RDTHost(self, EventEntity.A, self.timer_interval, 5)
        # These variables will be used by the testing suite
        self.A.num_data_sent = 0
        self.A.num_ack_sent = 0
        self.A.num_data_received = 0
        self.A.num_ack_received = 0
        self.A.data_sent = []
        self.A.data_received = []
               
        self.B = RDTHost(self, EventEntity.B, self.timer_interval, 5)
        self.B.num_data_sent = 0
        self.B.num_ack_sent = 0
        self.B.num_data_received = 0
        self.B.num_ack_received = 0
        self.B.data_sent = []
        self.B.data_received = []
        
        self.Host = {
            EventEntity.A: self.A,
            EventEntity.B: self.B,
        }

        self.test_name = test_name
        self.A_as_sender_log = open(f"{test_name}--ASending.log", "w")
        self.B_as_sender_log = open(f"{test_name}--BSending.log", "w")

        # Generate the first event
        self.generate_next_arrival()


    def Simulate(self):
        #print("-----  Sliding Window Network Simulator Version -------- \n")

        events = []

        while self.continue_simulation:
            # Check to see if we have any more events to simulate
            if len(self.event_list) == 0:
                self.continue_simulation = False
                #self.trace("Simulator terminated at time {} after sending {} msgs from layer5\n".format(self.time, self.nsim), 0)
                #print("Simulator terminated at time {} after sending {} msgs from layer5\n".format(self.time, self.nsim))
            else:
                # Get the next event to simulate
                cur_event = self.event_list.pop(0)
                events.append(cur_event)

                # update our time value to the time of the next event
                self.time = cur_event.evtime 

                # This is an event containing new data from the application layer
                if cur_event.evtype == EventType.FROM_APPLICATION_LAYER:
                    # Set up the next packet to arrive after this one
                    self.generate_next_arrival()

                    payload = self.generate_payload()

                    events[-1].pkt=payload

                    # Incrememnt the number of packets that have been simulated
                    self.nsim += 1

                    # Log this event
                    self.Host[cur_event.eventity].data_sent.append(payload)
                    self.print_entity_message(cur_event.eventity, "Rcvd from Application Layer: %s" % payload, None)
                    self.print_to_log(cur_event.eventity, cur_event.eventity, "Rcvd from Application Layer: %s" % payload, None)

                    # Send this message to the assigned host
                    self.Host[cur_event.eventity].receive_from_application_layer(payload)

                # This is an event being passed up from the network layer
                elif cur_event.evtype == EventType.FROM_NETWORK_LAYER:
                    # Log this event
                    self.print_entity_message(cur_event.eventity, "Rcvd from Network Layer", cur_event.pkt)

                    if not self.packet_is_ack(cur_event.pkt):
                        self.print_to_log(self.opposite_entity(cur_event.eventity), cur_event.eventity, "Rcvd from Network Layer", cur_event.pkt)
                    else:
                        self.print_to_log(cur_event.eventity, cur_event.eventity, "Rcvd from Network Layer", cur_event.pkt)                        

                    # Send this message to the assigned host
                    self.Host[cur_event.eventity].receive_from_network_layer(cur_event.pkt)

                # This is a timer interrupt event
                elif cur_event.evtype == EventType.TIMER_INTERRUPT:
                    self.print_entity_message(cur_event.eventity, "Timer Interrupt", None)
                    self.print_to_log(cur_event.eventity, cur_event.eventity, "Timer Interrupt", None)
                    self.Host[cur_event.eventity].timer_interrupt()
        
        self.A_as_sender_log.close()
        self.B_as_sender_log.close()
        
        with open(f"{self.test_name}_events.json", "w") as outfile:            
            dict = json.dumps(events, cls=ComplexEncoder, indent=4)
            outfile.write(dict)

        return events


    def opposite_entity(self, entity):
        if entity == EventEntity.A:
            return EventEntity.B
        else: 
            return EventEntity.A


    def create_entity_message(self, entity, message, bytes):
        msg = "{} @ {:.4f}: {}".format(entity.name, self.time, message)

        if bytes:
            try:
                pkt = self.Host[entity].unpack_pkt(bytes)
                if pkt:
                    # If this is a data packet
                    if pkt["packet_type"] == 0x00:
                        msg += f": [TYPE: DATA, SEQ: {pkt['seq_num']}, CKSUM: {pkt['checksum']}, LEN: {pkt['payload_length']}, PAYLOAD: {pkt['payload']}]"
                    elif pkt["packet_type"] == 0x01:
                        msg += f": [TYPE: ACK, SEQ: {pkt['seq_num']}, CKSUM: {pkt['checksum']}]"

            except struct.error as e:
                # Likely indicates a corrupted packet
                msg += "ERROR" #" -- EXCEPTION: " + str(e)
            except Exception as e:
                # Some other exception, probably raised by student code
                msg += "ERROR" #" -- EXCEPTION: " + str(e)

        return msg

    
    def print_entity_message(self, entity, message, bytes):
        #print(self.create_entity_message(entity, message, bytes))
        pass
        

    def create_entity_log_message(self, entity, message, bytes):
        msg = "{} @ {:.4f}: {}".format(entity.name, self.time, message)

        if bytes:
            try:
                pkt = self.Host[entity].unpack_pkt(bytes)
                if pkt:
                    # If this is a data packet
                    if pkt["packet_type"] == 0x00:
                        msg += f": [TYPE: DATA, SEQ: {pkt['seq_num']}, CKSUM: {pkt['checksum']}, LEN: {pkt['payload_length']}, PAYLOAD: {pkt['payload']}]"
                    elif pkt["packet_type"] == 0x01:
                        msg += f": [TYPE: ACK, SEQ: {pkt['seq_num']}, CKSUM: {pkt['checksum']}]"

            except struct.error as e:
                # Likely indicates a corrupted packet
                msg += " -- EXCEPTION: " + str(e)
            except Exception as e:
                # Some other exception, probably raised by student code
                msg += " -- EXCEPTION: " + str(e)

        return msg



    
    def print_to_log(self, sending_entity, event_entity, message, bytes):
        msg = self.create_entity_log_message(event_entity, message, bytes)
        if sending_entity == EventEntity.A:
            self.A_as_sender_log.write(msg + "\n")
        else:
            self.B_as_sender_log.write(msg + "\n")


    def generate_payload(self):
        # Create a simulated message for this packet
        j = self.nsim % 26
        msg2give = ""
        length = random.randint(2, 5)
        for i in range(0,length):
            msg2give += chr(97 + j)
        return msg2give


    def generate_next_arrival(self):
        if self.num_events < self.max_events:
            self.num_events += 1

            # Create a new simulated event
            new_event = SimulatedEvent()

            # Determine when this simulated event will occur
            x = self.arrival_rate*random.uniform(0.0, 1.0)*2  # x is uniform on [0,2*lambda], having mean of lambda
            new_event.evtime = self.time + x

            # Specify that this event is coming from the application layer
            new_event.evtype = EventType.FROM_APPLICATION_LAYER

            # Determine which host is receiving this event, A or B
            if random.uniform(0.0, 1.0) > 0.5:
                new_event.eventity = EventEntity.A
            else:
                new_event.eventity = EventEntity.B

            # Insert the new event into our event list
            self.insert_event(new_event)


    def insert_event(self, new_event):
        # If queue is empty, add as head and don't connect any adjacent events
        if len(self.event_list) == 0:
            self.event_list.append(new_event)
        else:
            # check to see if this event occurs before the first element
            if new_event.evtime < self.event_list[0].evtime:
                self.event_list.insert(0, new_event)
            # check to see if this event occurs after the last element\
            elif new_event.evtime > self.event_list[-1].evtime:
                self.event_list.append(new_event)
            else:
                for idx, e in enumerate(self.event_list):
                    if new_event.evtime < e.evtime:
                        self.event_list.insert(idx, new_event)
                        break


    def print_event_list(self, trace_level):
        for e in self.event_list:
            #self.trace("Event time: {}, type: {} entity: {}".format(e.evtime, e.evtype, e.eventity),trace_level)
            pass


    def packet_is_ack(self, packet):
        # Determine if this is an ACK packet based on the first byte
        return struct.unpack("!H", packet[0:2])[0] == 0x1



    # ******** DO NOT CALL ANY ROUTINES IN Simulator ABOVE THESE LINES ********
    # *********************** Student callable routines ***********************
    # ********* You will need to call the routines below these lines **********
    
    def pass_to_network_layer(self, entity, packet):
        self.ntolayer3 += 1

        # Determine if this is an ACK packet based on the first byte
        is_ACK = self.packet_is_ack(packet)
        
        if is_ACK:
            self.Host[entity].num_ack_sent += 1
        else:
            self.Host[entity].num_data_sent += 1

        self.print_entity_message(entity, "Passing to Network Layer", packet)
        
        if is_ACK:
            self.print_to_log(self.opposite_entity(entity), entity, "Passing to Network Layer", packet)
        else:
            self.print_to_log(entity, entity, "Passing to Network Layer", packet)                        


        # Simulate losses
        if random.uniform(0.0, 1.0) < self.lossprob:
            self.nlost += 1
            self.print_entity_message(entity, "LOSING PACKET!", None)
            if is_ACK:
                self.print_to_log(self.opposite_entity(entity), entity, "LOSING PACKET!", packet)
            else:
                self.print_to_log(entity, entity, "LOSING PACKET!", packet)   
            
            loss_event = SimulatedEvent()
            loss_event.evtype = EventType.PACKET_LOSS
            loss_event.eventity = entity
            loss_event.pkt = copy.deepcopy(packet)
            self.insert_event(loss_event)

            #self.trace("TOLAYER3: PACKET BEING LOST", 0)
            return

        if is_ACK:
            self.Host[self.opposite_entity(entity)].num_ack_received += 1
        else:
            self.Host[self.opposite_entity(entity)].num_data_received += 1

        # make a copy of the packet student just gave me since he/she may decide
        # to do something with the packet after we return back to him/her
        pkt = copy.deepcopy(packet)
        try:
            #self.trace("TOLAYER3: seq: {}, ack {}, check: {}, {}".format(pkt.seqnum, pkt.acknum, pkt.checksum, pkt.payload), 2)
            pass
        except Exception as e:
            pass

        new_event = SimulatedEvent()
        new_event.evtype = EventType.FROM_NETWORK_LAYER
        new_event.eventity = EventEntity((int(entity)+1) % 2)     # event occurs at the other entity
        new_event.pkt = pkt

        # finally, compute the arrival time of packet at the other end.
        # medium can not reorder, so make sure packet arrives between 1 and 10
        # time units after the latest arrival time of packets
        # currently in the medium on their way to the destination
        last_time = self.time
        for e in self.event_list:
            if e.evtype == EventType.FROM_NETWORK_LAYER and e.eventity == entity:
                last_time = e.evtime
        new_event.evtime = last_time + 0.1 + 0.9*random.uniform(0.0, 1.0)

        # simulate corruption
        if random.uniform(0.0, 1.0) < self.corruptprob:
            self.ncorrupt += 1
            self.print_entity_message(entity, "CORRUPTING PACKET!", None)
            if is_ACK:
                self.print_to_log(self.opposite_entity(entity), entity, "CORRUPTING PACKET!", packet)
            else:
                self.print_to_log(entity, entity, "CORRUPTING PACKET!", packet)     
                
            # Flip a random bit
            bytenum = random.randint(0, len(pkt)-1)
            bitnum = random.randint(0, 7)
            values = bytearray(pkt)
            altered_value = values[bytenum]
            bit_mask = 1 << bitnum
            values[bytenum] = altered_value ^ bit_mask
            new_event.pkt = bytes(values)

            corrupt_event = SimulatedEvent()
            corrupt_event.evtype = EventType.CORRUPT_PACKET
            corrupt_event.eventity = entity
            corrupt_event.pkt = pkt
            self.insert_event(corrupt_event)

        #self.trace("TOLAYER3: scheduling arrival on other side", 2)
        self.insert_event(new_event)



    def pass_to_application_layer(self, entity, data):
        # Log this event
        self.Host[entity].data_received.append(data)
        self.print_entity_message(entity, "Passing to Application Layer: %s" % data, None)
        self.print_to_log(self.opposite_entity(entity), entity, "Passing to Application Layer: %s" % data, None)
        


    def start_timer(self, entity, increment):
        # Check to see if a timer has already been started
        for e in self.event_list:
            if e.evtype == EventType.TIMER_INTERRUPT and e.eventity == entity:
                self.print_entity_message(entity, "WARNING: ATTEMPTED TO START TIMER WHILE ONE IS ALREADY RUNNING", None)
                self.print_to_log(entity, entity, "WARNING: ATTEMPTED TO START TIMER WHILE ONE IS ALREADY RUNNING", None)
                return

        self.print_entity_message(entity, "Starting Timer", None)
        self.print_to_log(entity, entity, "Starting Timer", None)

        new_event = SimulatedEvent()
        new_event.evtime = self.time + increment
        new_event.evtype = EventType.TIMER_INTERRUPT
        new_event.eventity = entity
        self.insert_event(new_event)
        
        

    def stop_timer(self, entity):
        for idx, e in enumerate(self.event_list):
            if e.eventity == entity:
                if e.evtype == EventType.TIMER_INTERRUPT:
                    self.event_list.pop(idx)    # Remove the first timer event associated with this entity
                    self.print_entity_message(entity, "Stopping Timer", None)
                    self.print_to_log(entity, entity, "Stopping Timer", None)
                    return
                else:
                    # No timer event to stop
                    pass
        self.print_entity_message(entity, "ERROR: ATTEMPTED TO STOP A TIMER BUT NONE WERE RUNNING", None)
        self.print_to_log(entity, entity, "WARNING: ATTEMPTED TO STOP A TIMER BUT NONE WERE RUNNING", None)



class SimulatedEvent():
    def __init__(self):
        self.evtime = 0
        self.evtype = None
        self.eventity = None
        self.pkt = None
        self.previous_event = None
        self.next_event = None
                

class EventType(str, Enum):
    FROM_APPLICATION_LAYER = "FROM_APPLICATION_LAYER"
    FROM_NETWORK_LAYER = "FROM_NETWORK_LAYER"
    TIMER_INTERRUPT = "TIMER_INTERRUPT"
    CORRUPT_PACKET = "CORRUPT_PACKET"
    PACKET_LOSS = "PACKET_LOSS"


class EventEntity(IntEnum):
    A = 0
    B = 1

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SimulatedEvent):
            obj_dict = {key: str(obj.__dict__[key]) for key in obj.__dict__}
            return obj_dict
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)