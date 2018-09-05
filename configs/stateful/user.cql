// Test Data for 3-node Cassandra cluster in Kubernetes.


CREATE KEYSPACE IF NOT EXISTS test_data WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 3
};

USE test_data;

CREATE TABLE IF NOT EXISTS user (
    first_name text,
    last_name text,
    PRIMARY KEY (first_name));

INSERT INTO user (first_name, last_name) VALUES ('bob', 'odenkirk');
INSERT INTO user (first_name, last_name) VALUES ('saul', 'goodman');
INSERT INTO user (first_name, last_name) VALUES ('mike', 'hermantrout');

SELECT * FROM user;
