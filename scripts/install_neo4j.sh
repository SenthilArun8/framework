#!/bin/bash
cd /mnt/c/Users/senth/Downloads/framework
# Convert RPM to DEB. --scripts is important to include pre/post install scripts.
alien --to-deb --scripts neo4j-2025.10.1-1.noarch.rpm
# Install the generated DEB (filename might vary slightly, so we use wildcard)
dpkg -i neo4j*.deb
