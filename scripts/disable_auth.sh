#!/bin/bash
# Uncomment and ensure it is set to false
sed -i 's/#dbms.security.auth_enabled=false/dbms.security.auth_enabled=false/' /etc/neo4j/neo4j.conf
# Also handle case where it might be true
sed -i 's/dbms.security.auth_enabled=true/dbms.security.auth_enabled=false/' /etc/neo4j/neo4j.conf

# Restart
neo4j restart
