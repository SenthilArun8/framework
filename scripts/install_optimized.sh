#!/bin/bash
set -e
# Copy to tmp for speed
echo "Copying to /tmp..."
cp /mnt/c/Users/senth/Downloads/framework/neo4j-2025.10.1-1.noarch.rpm /tmp/
cd /tmp

# Convert
echo "Converting RPM to DEB..."
alien --to-deb --scripts neo4j-2025.10.1-1.noarch.rpm

# Install
echo "Installing DEB..."
dpkg -i neo4j*.deb

# Configure
echo "Configuring..."
sed -i 's/#server.default_listen_address=0.0.0.0/server.default_listen_address=0.0.0.0/' /etc/neo4j/neo4j.conf

echo "Done."
