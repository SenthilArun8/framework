#!/bin/bash
add-apt-repository -y ppa:openjdk-r/ppa
apt-get update
apt-get install -y openjdk-21-jdk
update-alternatives --set java /usr/lib/jvm/java-21-openjdk-amd64/bin/java
java -version
neo4j console
