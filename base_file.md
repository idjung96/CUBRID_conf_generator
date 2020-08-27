# Description of base file for generating conf files

### Example ###
```
svc_name: 'basic'
max_clients: '200'
pc_ip:
  - '10.0.2.10'
  - '134.134.*'
app_ip:
  - '10.0.2.20'
  - '111.111.111.111'
  - '133.133.133.133' 
svr_info:
  - name: 'center'
    ip: '10.0.2.10'
  - name: 'cubrid1'
    ip: '10.0.2.20'    
role_info:
  - db: 'basic'
    ha: 'center:cubrid1'
broker_info:
  - location: 'center'
    brokers: 
      - name: 'brk1'
        mode: 'rw'
        port: '33000'
        min_cas: '20'
        max_cas: '30'
        svc_on_off: 'on'
        db: 'basic'
      - mode: 'rw'
        name: 'brk2'
        port: '34000'
        db: 'basic'
  - location: cubrid1
    brokers: 
      - name: 'brk1'
        mode: 'rw'
        port: '33000'
        min_cas: '20'
        max_cas: '30'
        svc_on_off: 'on'
        db: 'basic'
      - mode: 'rw'
        name: 'brk2'
        port: '34000'
        db: 'basic'
```

### Elements ###
1. svc_name: service name(directory name) where generated config files are stored. Usually the same name as the playbook's var 'db_name' 
2. max_clients: It is used in the max_clients parameter of cubrid.conf, and at least max_clients is recommended by using the broker configuration when creating the cubrid.conf file.
3. pc_ip: IP Address of PC used by DBA. ACL for CUBRID Manager
4. app_ip: IP Address of Application Server
5. svr_info: Server Information. IP Address and hostname. It must be equal to information in /etc/hosts
  - name: 'center'
    ip: '10.0.2.10'
  - name: 'cubrid1'
    ip: '10.0.2.20'    
6. role_info: HA Information. This includes Active-Standby Servers and Replica Servers
7. broker_info: Broker Information. refer to example
