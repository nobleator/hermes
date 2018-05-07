clients = ['cid,name,description,deleted',
           '1,Doug Dimmadome,Owner of the Dimmsdale Dimmadome,false',
           '2,Bob Vance,Vance Refrigeration,false',
           '3,Homer Simpson,Nuclear technician,false']
with open('clients.csv', 'w') as fid:
    fid.write('\n'.join(clients))

sites = ['sid,address,deleted',
         '1,100 Maple Road,false',
         '2,7 Main Street,false',
         '3,1600 Pennsylvania Avenue,false']
with open('sites.csv', 'w') as fid:
    fid.write('\n'.join(sites))

orders = ['oid,cid,sid,due,status,deleted',
          '1,1,1,4 May 2018,Order placed,false',
          '2,2,2,25 December 2018,Delivery scheduled,false',
          '3,3,3,1 April 2018,Order completed,false']
with open('orders.csv', 'w') as fid:
    fid.write('\n'.join(orders))


"""
postgres commands:
CREATE DATABASE hermes;
\connect hermes
CREATE TABLE users (uid TEXT,
                    username TEXT,
                    email TEXT,
                    password TEXT,
                    created_on TIMESTAMP);

CREATE TABLE clients (cid TEXT PRIMARY KEY,
                      name TEXT,
                      description TEXT,
                      deleted BOOLEAN);
\copy clients FROM 'clients.csv' WITH CSV HEADER

CREATE TABLE sites (sid TEXT PRIMARY KEY,
                    address TEXT,
                    deleted BOOLEAN);
\copy sites FROM 'sites.csv' WITH CSV HEADER

CREATE TABLE orders (oid TEXT PRIMARY KEY,
                     cid TEXT REFERENCES clients (cid),
                     sid TEXT REFERENCES sites (sid),
                     due TEXT,
                     status TEXT,
                     deleted BOOLEAN);
\copy orders FROM 'orders.csv' WITH CSV HEADER
"""
