#!/bin/bash
# OCI Keep-Alive Script
# Generates ~60 seconds of light CPU activity at ~25% of 1 core
# Just enough to register as "active" without stressing the system
#
# Installation:
#   sudo cp oci-keepalive.sh /usr/local/bin/
#   sudo chmod +x /usr/local/bin/oci-keepalive.sh
#
# Crontab (runs every hour):
#   0 * * * * /usr/local/bin/oci-keepalive.sh
#
# To add to crontab:
#   (crontab -l 2>/dev/null; echo "0 * * * * /usr/local/bin/oci-keepalive.sh") | crontab -

# Light compression work (uses 1 core partially)
dd if=/dev/urandom bs=1M count=50 2>/dev/null | gzip > /dev/null

# Small math computation
for i in $(seq 1 1000); do
  echo "scale=100; 4*a(1)" | bc -l > /dev/null 2>&1
done
