// Copyright (c) 2020 AlertAvert.com  All rights reserved.
// Created by M. Massenzio
//
// Creates a Mongo Replica Set.
// TODO: make the number of nodes and their DNS names configurable.

const clustersize = 3
const nodename = "mongo-node-";
const clustername = ".mongo-cluster";

let nodes = [];

for(let i = 0; i < clustersize; i = i +1) {
    nodes[i] = {_id: i, host: nodename + i + clustername};
}

rs.initiate({
    _id: "rs0",
    members: nodes
  }
);

// Emit the status of the ReplicaSet to console, so
// that it is visible in the logs for diagnostics.
printjson(rs.status());
