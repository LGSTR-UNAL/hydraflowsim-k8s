FROM quay.io/strimzi/kafka:0.43.0-kafka-3.7.0
USER root:root

# --- Directory for Kafka Connect Plugins ---
RUN mkdir -p /opt/kafka/plugins/

# --- Directory for Apache Camel plugins ---
RUN mkdir -p /opt/kafka/plugins/camel/
# camel sjms2
# https://camel.apache.org/camel-kafka-connector/3.18.x/reference/connectors/camel-sjms2-kafka-source-connector.html
RUN curl https://repo1.maven.org/maven2/org/apache/camel/kafkaconnector/camel-sjms2-kafka-connector/3.20.0/camel-sjms2-kafka-connector-3.20.0-package.tar.gz \
    -o /opt/kafka/plugins/camel/camel-sjms2-kafka-connector-3.20.0-package.tar.gz \
    && tar xzvf /opt/kafka/plugins/camel/camel-sjms2-kafka-connector-3.20.0-package.tar.gz -C /opt/kafka/plugins/camel/ \
    && rm /opt/kafka/plugins/camel/camel-sjms2-kafka-connector-3.20.0-package.tar.gz

# --- Directory for Debezium plugins ---
RUN mkdir -p /opt/kafka/plugins/debezium
# debezium postgres connector
# https://debezium.io/documentation/reference/stable/connectors/postgresql.html
RUN curl https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.1.3.Final/debezium-connector-postgres-2.1.3.Final-plugin.tar.gz \
    -o /opt/kafka/plugins/debezium/debezium-connector-postgres-2.1.3.Final-plugin.tar.gz \
    && tar xzvf /opt/kafka/plugins/debezium/debezium-connector-postgres-2.1.3.Final-plugin.tar.gz -C /opt/kafka/plugins/debezium/ \
    && rm /opt/kafka/plugins/debezium/debezium-connector-postgres-2.1.3.Final-plugin.tar.gz

# https://debezium.io/documentation/reference/stable/connectors/postgresql.html
# --- Directory for Confluent plugins ---
RUN mkdir -p /opt/kafka/plugins/confluent
# confluent jdbc connector
# https://debezium.io/documentation/reference/stable/connectors/mongodb.html
RUN curl https://d2p6pa21dvn84.cloudfront.net/api/plugins/confluentinc/kafka-connect-jdbc/versions/10.7.12/confluentinc-kafka-connect-jdbc-10.7.12.zip \
    -o /opt/kafka/plugins/confluent/confluentinc-kafka-connect-jdbc-10.7.12.zip \
    && unzip -qq /opt/kafka/plugins/confluent/confluentinc-kafka-connect-jdbc-10.7.12.zip -d /opt/kafka/plugins/confluent/ \
    && rm /opt/kafka/plugins/confluent/confluentinc-kafka-connect-jdbc-10.7.12.zip

# --- Directory for community plugins
RUN mkdir -p /opt/kafka/plugins/community
# Xml Transformations
# https://jcustenborder.github.io/kafka-connect-documentation/projects/kafka-connect-transform-xml/index.html
RUN curl https://repo1.maven.org/maven2/com/github/jcustenborder/kafka/connect/kafka-connect-transform-xml/0.1.0.4/kafka-connect-transform-xml-0.1.0.4.tar.gz \
    -o /opt/kafka/plugins/community/kafka-connect-transform-xml-0.1.0.4.tar.gz \
    && tar xzvf /opt/kafka/plugins/community/kafka-connect-transform-xml-0.1.0.4.tar.gz -C /opt/kafka/plugins/community/ \
    && rm /opt/kafka/plugins/community/kafka-connect-transform-xml-0.1.0.4.tar.gz
# Common Transformations
# https://jcustenborder.github.io/kafka-connect-documentation/projects/kafka-connect-transform-common/index.html
RUN curl https://repo1.maven.org/maven2/com/github/jcustenborder/kafka/connect/kafka-connect-transform-common/0.1.0.14/kafka-connect-transform-common-0.1.0.14.tar.gz \
    -o /opt/kafka/plugins/community/kafka-connect-transform-common-0.1.0.14.tar.gz \
    && tar xzvf /opt/kafka/plugins/community/kafka-connect-transform-common-0.1.0.14.tar.gz -C /opt/kafka/plugins/community/ \
    && rm /opt/kafka/plugins/community/kafka-connect-transform-common-0.1.0.14.tar.gz

USER 1001