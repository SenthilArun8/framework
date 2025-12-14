#!/bin/bash
# Configure Neo4j to listen on all interfaces
sed -i 's/#server.default_listen_address=0.0.0.0/server.default_listen_address=0.0.0.0/' /etc/neo4j/neo4j.conf
# Start Neo4j
neo4j console
