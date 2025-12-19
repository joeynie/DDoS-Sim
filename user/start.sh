#!/bin/bash

echo "Adding route to 10.10.20.0/24 via 10.10.10.5..."
ip route add 10.10.20.0/24 via 10.10.10.5

echo "Starting user traffic simulator..."
python3 ./user_traffic_simulator.py