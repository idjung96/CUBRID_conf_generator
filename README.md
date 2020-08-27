# ansible_for_cubrid

### Background ###
The most useful feature of CUBRID is HA (High Availability), which can provide uninterrupted service even when a failure occurs in H/W, OS, and network. CUBRID HA ensures database synchronization among multiple servers when providing service. 
CUBRID HA is supported by the CUBRID engine, so it can be used without a separate package or S/W. In addition, there is no need to purchase additional licenses, so there is no need for IT infrastructure costs.
CUBRID HA is the most outstanding feature of CUBRID, but it is difficult to use because there are many configuration file such as databases.txt, cubrid_ha.conf and so on.

### Object ###
The object is to develop tools that supports CUBRID HA operation such as DB construction, upgrade, and DB reconstruction so that many software developers can easily use CUBRID HA.

### Preparation ###
1. add server info to /etc/hosts 
```
$ vi /etc/hosts
10.0.2.10   center
10.0.2.20   cubrid1
```
2. copy ssh key file with 'ssh-copy-id' 
```
$ ssh-copy-id ~/.ssh/id_rsa.pub root@center
```

### Installation ###
1. install role
```
$ ansible-galaxy install singleplatform-eng.users
$ ansible-galaxy install idjung96.cubrid_installer
```

2. install python3
```
$ yum install python3 python3-devel
```

### Practice ###
1. make a base file for generating configuration(.yml)
```
$ vi exam.yml
svc_name: 'basic'
max_clients: '200'
pc_ip:
  - '10.0.2.10'
  - '134.134.*'
...
        port: '34000'
        db: 'basic'
...
```

2. generate configuration files for cubrid
```
$ python3 get_cub_conf.py cubrid1 svc.yml
```

3. copy configuration filea to 'files' folder in ansible folder 
```
$ cp -a svc_folder/* ~/.ansible/files/
```

4. make hosts file
```
$ vi hosts
[cubrid]
center
cubrid1
```

5. make playbook file (.yml)
```
$ vi play.yml
- hosts: all
  name: cubrid installer
  vars:
# modifiable start --------------------------
    cubrid_account: "cubrid1"
    config_dir: "/root/.ansible"
    cubrid_ver: "10.2"
    db_name: basic
    create_db: true
# modifiable end ---------------------------
    cubrid_platform: "x86_64"
    groups_to_create:
      - name: "cubrid"
        gid: "10000"
    users:
      - username: "{{ cubrid_account }}"
        name: "{{ cubrid_account }}"
        group: 'cubrid'
  roles:
    - singleplatform-eng.users
    - cubrid.installer
```

6. execute ansible with playbook
```
$ ansible-playbook -i hosts play.yml
```
