FROM fedora:39

# Copy the RPM file into the container
COPY neo4j-2025.10.1-1.noarch.rpm /tmp/neo4j.rpm

# Install Java 17 (required for newer Neo4j versions) and the Neo4j RPM
# We use dnf localinstall to handle dependencies automatically
RUN dnf update -y && \
    dnf install -y java-17-openjdk && \
    dnf install -y /tmp/neo4j.rpm && \
    dnf clean all

# Expose HTTP and Bolt ports
EXPOSE 7474 7687

# Configure Neo4j to allow remote connections (needed for Docker)
RUN sed -i 's/#server.default_listen_address=0.0.0.0/server.default_listen_address=0.0.0.0/' /etc/neo4j/neo4j.conf

# Start Neo4j
CMD ["neo4j", "console"]
