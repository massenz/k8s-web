// Copyright (c) 2020 AlertAvert.com  All rights reserved.
// Created by M. Massenzio
//
// Creates a Mongo Replica Set.

let nodes = [];
for(let i = 0; i < clustersize; i = i +1) {
    nodes[i] = {_id: i, host: nodename + "-" + i + "." + clustername};
}

rs.initiate({
    _id: "rs0",
    members: nodes
  }
);

// Emit the status of the ReplicaSet to console, so
// that it is visible in the logs for diagnostics.
printjson(rs.status());
