import yaml
import sys
import argparse
import os
import datetime

def get_role(setup_info, server):
    role_dict = {}
    for r_info in setup_info['role_info']:
        replica_list = []
        server_list = []
        server_list = r_info['ha'].split(':')
        if 'replica' in r_info:
            replica_list = r_info['replica'].split(':')    
    
        if len(server_list) == 1 and server_list[0] == server:
            role_dict[r_info['db']] = 'single'
            continue
        server_index = server_list.index(server) if server in server_list else -1  
        if server_index == 0:
            role_dict[r_info['db']] = 'active'
            continue
        elif server_index >= 1:
            role_dict[r_info['db']] = 'standby'
            continue
        replica_index = replica_list.index(server) if server in replica_list else -1
        if replica_index >= 0:
            role_dict[r_info['db']] = 'replica'
            continue
        
        for b_info in setup_info['broker_info']:
            if b_info['location'] == server:
                for broker in b_info['brokers']:
                    if broker['db'] == r_info['db'] and r_info['db'] not in role_dict:
                        role_dict[r_info['db']] = 'broker-only'
    return role_dict

def make_unique_dir(dir_name):
    if os.path.isdir(dir_name) == False:          
        os.mkdir(dir_name)
    else:
        cur_time = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
        dir_name = dir_name + '_' + cur_time
        os.mkdir(dir_name)
    
    return dir_name

def make_setup_dir(setup_info):  
    svc_name = ''
      
    if 'svc_name' in setup_info:
        svc_name = setup_info['svc_name']
    else:
        svc_name = setup_info['svr_info'][0]['name']

    dir_name = make_unique_dir(svc_name)    
    os.chdir(dir_name)
    for t_item in setup_info['svr_info']:
        # unique directory name because parent directory name is changed
        os.mkdir(t_item['name'])
    
    return dir_name        

def get_ha_role_info(setup_info, db_name, server):
    for r_info in setup_info['role_info']:
        server_list = r_info['ha'].split(':')
        if r_info['db'] == db_name and server in server_list:
            return r_info['ha']
        if 'replica' in r_info:
            replica_list = r_info['replica'].split(':')
            if r_info['db'] == db_name and server in replica_list:
                return r_info['replica']    
    return 'error'

def generate_databases_file(setup_info):
    for s_item in setup_info['svr_info']:
        f = open(os.path.join(s_item['name'],'databases.txt'),'a+')
        db_role_pair = get_role(setup_info=setup_info, server=s_item['name'])
        for db_name in db_role_pair.keys():
            ha_info = get_ha_role_info(setup_info=setup_info, db_name=db_name, server=s_item['name'])
            if ha_info == 'error':
                continue
            if db_role_pair[db_name] == 'single' or db_role_pair[db_name] == 'active' or \
                db_role_pair[db_name] == 'standby' or db_role_pair[db_name] == 'replica':                
                f.writelines(db_name + '   ' + '/home/'+setup_info['account']+'/DB    ' + 
                             ha_info + '    /home/'+setup_info['account']+'/DB/log')
            else:
                continue
    return True

# all server have same hosts file
def generate_hosts_file(setup_info):    
    f = open('hosts','a+')
    for t_item in setup_info['svr_info']:
        f.writelines(t_item['ip']+'    '+t_item['name']+'\n')
    f.close()           
    return True

def generate_ha_conf_file(setup_info):
    ha_conf_template = '''
[common]
ha_apply_max_mem_size=500 
ha_port_id=%s
ha_node_list=%s
ha_copy_sync_mode=%s
ha_db_list=%s   
    '''    
    num_part = setup_info["account"][6:]
    ha_info = []
    for s_item in setup_info['svr_info']:
        f = open(os.path.join(s_item['name'],'cubrid_ha.conf'),'a+')
        db_role_pair = get_role(setup_info=setup_info, server=s_item['name'])
        for db_name in db_role_pair.keys():
            role_info = setup_info['role_info']
            role_info_ha = [ db_info for db_info in role_info if db_info['db'] == db_name ]
            ha_info = dict(role_info_ha[0])
            ha_svr = ha_info['ha'].split(':')
            sync_mode = ['sync'] * (len(ha_svr))
            sync_mode_str = ':'.join(sync_mode) 
            f.writelines(ha_conf_template % ('cubrid'+num_part, 'cubrid@'+ha_info['ha'], sync_mode_str, db_name))
            if 'replica' in ha_info:
                f.writelines('ha_replica_list=cubrid@'+ha_info['replica'])
        f.close()
    return True

def generate_db_acl_file(setup_info):
    ip_list = []
    db_list = []
    for s_item in setup_info['svr_info']:
        ip_list.append(s_item['ip'])

    for b_info in setup_info['role_info']:
        db_list.append(b_info['db'])
    
    db_set = list(set(db_list))    
    ip_set = list(set(ip_list))
    for s_item in setup_info['svr_info']:
        f = open(os.path.join(s_item['name'],'db.access'),'a+')
        for d_item in db_set:
            acl_info = list(ip_set)
            acl_info.insert(0,'[@%s]' % d_item)
            acl_info.append('\n')
            acl_str = "\n".join(acl_info)
            f.write(acl_str)
        f.close()            
        
    return True

def generate_broker_acl_file(setup_info):
    if not 'app_ip' in setup_info:
        setup_info['app_ip'] = '*'    

    for b_item in setup_info['broker_info']:
        f = open(os.path.join(b_item['location'],'broker.access'),'a+')
        f.write('[%qe_so]\n*\n\n')
        f.write('[%qe_rw]\n*\n\n') 
        for s_item in b_item['brokers']:
            broker_name = s_item['name']+'_'+s_item['mode']+'_'+s_item['db']
            acl_info = list(setup_info['app_ip'])
            acl_info.insert(0,'[%%%s]' % broker_name)
            acl_info.append('\n')
            acl_str = "\n".join(acl_info)
            f.write(acl_str)
        f.close()         
    
    return True

def get_valid_max_clients(setup_info, database):
    max_clients = 0
    for s_item in setup_info['broker_info']:
        for b_item in s_item['brokers']:
            try:
                if b_item['db'] == database:
                    max_clients += int(b_item['max_cas'])
            except:
                max_clients += 40          
    return max_clients

def generate_cub_conf_file(setup_info):
    cub_conf_template = '''
[service]
service=server,broker,manager

[common]
access_ip_control=yes
access_ip_control_file="%s/conf/db.access"
force_remove_log_archives=%s
cubrid_port_id=%s
max_clients=%s
log_max_archives=%s
ha_mode=%s
''' 
    num_part = setup_info["account"][6:]
    if not 'cubrid_port_id' in setup_info:
        setup_info['cubrid_port_id'] = '1'+num_part+'01'

    for s_item in setup_info['svr_info']:
        db_role_pair = get_role(setup_info, s_item['name'])
        force_remove_log_archives = ''
        ha_mode = ''
        db_role = db_role_pair.values()
        if 'single' in db_role:
            force_remove_log_archives = 'yes'
            ha_mode = 'off'
        elif 'replica' in db_role:
            force_remove_log_archives = 'replica'
            ha_mode = 'replica'
        elif 'active' in db_role  or 'standby' in db_role:
            force_remove_log_archives = 'no'
            ha_mode = 'on'
        else:
            # broker-only, error
            force_remove_log_archives = 'no'
                        
        if not 'log_max_archives' in setup_info:
            setup_info['log_max_archives'] = '40'
        
        f = open(os.path.join(s_item['name'],'cubrid.conf'),'a+')
        f.write(cub_conf_template % (setup_info['cubrid_home'], force_remove_log_archives, 
                                    setup_info['cubrid_port_id'], setup_info['max_clients'], 
                                    setup_info['log_max_archives'], ha_mode))
        f.close()
        
    return True

def generate_broker_conf_file(setup_info):
    num_part = setup_info["account"][6:]
    for b_item in setup_info['broker_info']:
        if not 'brokers' in b_item:
            continue
        if not 'location' in b_item:
            continue
        
        f = open(os.path.join(b_item['location'],'cubrid_broker.conf'),'a+')
        make_broker_common_conf(f, setup_info, num_part)
            
        for b_info in b_item['brokers']:
            make_each_broker_conf(f, b_info, num_part)

        f.close()
    return True

def make_each_broker_conf(fp, broker_info, num_part):
    broker_template='''
SERVICE                 =%s
BROKER_PORT             =%s
MIN_NUM_APPL_SERVER     =%s
MAX_NUM_APPL_SERVER     =%s
APPL_SERVER_SHM_ID      =%s
LOG_DIR                 =log/broker/sql_log
ERROR_LOG_DIR           =log/broker/error_log
SQL_LOG                 =ON
TIME_TO_KILL            =120
SESSION_TIMEOUT         =300
KEEP_CONNECTION         =AUTO
CCI_DEFAULT_AUTOCOMMIT  =ON
ACCESS_MODE             =%s    
    '''    
    if not 'mode' in broker_info:
        broker_info['mode'] = 'rw'    
    if not 'svc_on_off' in broker_info:
        broker_info['svc_on_off'] = 'on'
    if not 'port' in broker_info:
        broker_info['port'] = '3'+num_part+'000'
    if not 'min_cas' in broker_info:
        broker_info['min_cas'] = '20'
    if not 'max_cas' in broker_info:
        broker_info['max_cas'] = '40'
        
    broker_name = broker_info['name']+'_'+broker_info['mode']+'_'+broker_info['db']
    fp.write('''\n[%%%s]''' % broker_name)        
    fp.write( broker_template % (broker_info['svc_on_off'], broker_info['port'], 
                                 broker_info['min_cas'], broker_info['max_cas'], 
                                 broker_info['port'], broker_info['mode']))
    
    return True
      
def make_broker_common_conf(fp, setup_info, num_part): 
    broker_conf = """
# cubrid_broker.conf by gen_cub_conf.py
[broker]
MASTER_SHM_ID           =%s
ADMIN_LOG_FILE          =log/broker/cubrid_broker.log
ACCESS_CONTROL          =ON
ACCESS_CONTROL_FILE     =%s/conf/broker.access
    """
    broker_qe_so_conf = """
[%%qe_so]
SERVICE                 =ON
BROKER_PORT             =%s
MIN_NUM_APPL_SERVER     =1
MAX_NUM_APPL_SERVER     =5
APPL_SERVER_SHM_ID      =%s
LOG_DIR                 =log/broker/sql_log/qe_so
ERROR_LOG_DIR           =log/broker/error_log/qe_so
SLOW_LOG_DIR            =log/broker/slow_log/qe_so
SQL_LOG                 =ON
LOG_BACKUP              =ON
TIME_TO_KILL            =300
SESSION_TIMEOUT         =300
KEEP_CONNECTION         =AUTO
SOURCE_ENV              =%s/conf/cubrid.env
APPL_SERVER_MAX_SIZE    =70
ACCESS_MODE             =SO
    """
    broker_qe_rw_conf = """
[%%qe_rw]
SERVICE                 =ON
BROKER_PORT             =%s
MIN_NUM_APPL_SERVER     =1
MAX_NUM_APPL_SERVER     =20
APPL_SERVER_SHM_ID      =%s
LOG_DIR                 =log/broker/sql_log/qe_rw
ERROR_LOG_DIR           =log/broker/error_log/qe_rw
SLOW_LOG_DIR            =log/broker/slow_log/qe_rw
SQL_LOG                 =ON
LOG_BACKUP              =ON
TIME_TO_KILL            =300
SESSION_TIMEOUT         =300
KEEP_CONNECTION         =AUTO
SOURCE_ENV              =%s/conf/cubrid.env
APPL_SERVER_MAX_SIZE    =70
ACCESS_MODE             =RW    
    """
    if not 'master_shm_id' in setup_info:
        master_shm_id = '3'
        for i in range(0, 4-len(num_part)):
            master_shm_id += '0'
        master_shm_id += num_part
        setup_info['master_shm_id'] = master_shm_id
    fp.write( broker_conf % (setup_info["master_shm_id"], setup_info["cubrid_home"]))
    fp.write( broker_qe_so_conf % ('20'+num_part+'40', '20'+num_part+'40', setup_info["cubrid_home"]))
    fp.write( broker_qe_rw_conf % ('20'+num_part+'50', '20'+num_part+'50', setup_info["cubrid_home"]))

    return True

def is_valid_conf(setup_info):
    if not 'account' in setup_info:
        print('[ERR] MUST have \'account\' key')
        return False
            
    acc_str = setup_info['account']
    if acc_str[0:6] != 'cubrid':
        print('[ERR] MUST have cubrid account')
        return False

    if not 'svc_name' in setup_info:
        print('[ERR] MUST have \'svc_name\' key')
        return False

    if not 'cubrid_home' in setup_info:
        print('[ERR] MUST have \'cubrid_home\' key')
        return False       

    recommended_max_clients = 0
    for r_info in setup_info['role_info']:
        candidate_max_clients = get_valid_max_clients(setup_info, r_info['db'])
        if recommended_max_clients < candidate_max_clients:
            recommended_max_clients = candidate_max_clients    
        recommended_max_clients += 20
    if 'max_clients' in setup_info:
        if int(setup_info['max_clients']) < recommended_max_clients:
            print('[ERR] max_clients MUST be over %s' % str(recommended_max_clients))
            return False     
    else:
        setup_info['max_clients'] = str(recommended_max_clients)
    
    ip_list = []
    svr_name_list = []
    for s_item in setup_info['svr_info']:
        if not 'ip' in s_item:
            print('[ERR]: MUST have \'ip\' in '+s_item['name'])
            return False
        ip_list.append(s_item['ip'])
        
        if not 'name' in s_item:
            print('[ERR]: MUST have \'name\' in '+s_item['name'])
            return False            
        svr_name_list.append(s_item['name'])
    
    ip_set = list(set(ip_list))
    if len(ip_set) != len(ip_list):
        print('[ERR]: have duplicate ip address')
        return False       
    
    svr_name_set = list(set(svr_name_list))
    if len(svr_name_set) != len(svr_name_list):
        print('[ERR]: have duplicate server name')
        return False       

    for b_item in setup_info['broker_info']:
        broker_info_list = {}
        for b_info in b_item['brokers']:
            broker_list = []
            if not 'name' in b_info:
                print('[ERR]: MUST have broker \'name\' in '+b_item['location'])
                return False
            if not 'port' in b_info:
                print('[ERR]: MUST have broker \'port\' in '+b_item['location'])
                return False
            broker_list.append(b_info['port'])
        broker_info_list[b_info['db']]=broker_list
        
        for broker_info_list_key in broker_info_list.keys():
            list_len = len(broker_info_list[broker_info_list_key])
            set_len = len(list(set(broker_info_list[broker_info_list_key])))
            if list_len != set_len:
                print('[ERR]: have duplicate broker port')
                return False         
        
    for r_info in setup_info['role_info']:
        if not 'ha' in r_info:
            print('[ERR]: MUST have \'ha\' in '+r_info['db'])
            return False                         
    return True

# main 
if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Generator for CUBRID conf file')
    parser.add_argument('cubrid_user', metavar='cubrid_user', type=str, nargs=1,
                        help='account installing CUBRID')
    parser.add_argument('conf_file_name', metavar='conf_file', type=str, nargs=1,
                        help='a file for CUBRID setup info')
    args = parser.parse_args()

    try:
        yaml_file = open(args.conf_file_name[0])
        in_yaml = yaml.load(yaml_file, Loader=yaml.FullLoader)
        in_yaml['account'] = args.cubrid_user[0]
        in_yaml['cubrid_home'] = '/home/'+args.cubrid_user[0]+'/CUBRID'
    except:
        print('Not enough argument')
        parser.print_help()
        exit(0)
                
    if is_valid_conf(in_yaml) == False:
        print('Conf file error')
        exit(0)

    # setup_type = get_setup_type(in_yaml)
    
    setup_dir = make_setup_dir(in_yaml)
    generate_hosts_file(in_yaml)
    generate_cub_conf_file(in_yaml)
    generate_db_acl_file(in_yaml)
    generate_broker_conf_file(in_yaml)
    generate_broker_acl_file(in_yaml)
    generate_databases_file(in_yaml)
    generate_ha_conf_file(in_yaml)
