# Description of playbook for CUBRID

### Example ###
```
# todo: make simple urls for CUBRID repository
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

### vars ###

#### modifiable ####
1. cubrid_account: linux account to install and operate CUBRID. IMPORTANT! this must be equal to argument 'cubrid account' of get_cub_conf.py.
2. config_dir: Directory including ansible playbooks and roles 
3. cubrid_ver: CUBRID Version to install. cubrid.installer role will install the latest build of this version
4. db_name: Database name to be created
IMPORTANT! this must be equal to 'db' element in 'role_info' element in a base file.
5. create_db: true if you want to create database. This value is ignored if the database exists.

#### fixed ####
**DO NOT CHANGE these vars.**
1. cubrid_platform: OS platform 
2. groups_to_create: variable for singleplatform-eng.users role
3. users: variable for singleplatform-eng.users role
4. roles: ansible roles to use