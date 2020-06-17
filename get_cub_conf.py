import yaml
import sys
import argparse
import os
import datetime

def get_setup_type(setup_info):
    if len(setup_info['svr_info']) == 1:
        return 'single'
    return 'error'

def make_unique_dir(dir_name):
    if os.path.isdir(dir_name) == False:          
        os.mkdir(dir_name)
    else:
        cur_time = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
        dir_name = dir_name + '_' + cur_time
        print(dir_name)
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

def generate_hosts_file(svc_name, setup_info):    
    f = open('hosts','a+')
    for t_item in setup_info['svr_info']:
        f.write(t_item['ip']+'   '+t_item['name'])
    f.close()           
    return True

def gen_ha_conf_file():
    
    return True

def generate_access_control_file(setup_info):
    db_list = []
    ip_list = []
    for s_item in setup_info['svr_info']:
        ip_list.append(s_item['ip'])
        for d_info in s_item['databases']:
            db_list.append(d_info['name'])

    for s_item in setup_info['svr_info']:
        f = open(os.path.join(s_item['name'],'db_acl_file'),'a+')
        for d_item in db_list:
            acl_info = list(ip_list)
            acl_info.insert(0,'[@%s]' % d_item)
            acl_str = "\n".join(acl_info)
            f.write(acl_str)
        f.close()            
        
    return True

def get_valid_max_clients(setup_info):
    max_clients = 0
    for s_item in setup_info['svr_info']:
        for b_item in s_item['brokers']:
            try:
                max_clients += int(b_item['max_cas'])
            except:
                max_clients += 40          
    return max_clients

def generate_cub_conf_file(setup_type, setup_info):
    cub_conf_template = '''
[service]
service=server,broker,manager

[common]
data_buffer_size=512M
log_buffer_size=256M
sort_buffer_size=2M
access_ip_control=yes
force_remove_log_archives=%s
cubrid_port_id=%s
max_clients=%s
log_max_archives=%s
''' 
    num_part = setup_info["account"][6:]
    if not 'cubrid_port_id' in setup_info:
        setup_info['cubrid_port_id'] = '1'+num_part+'01'

    force_remove_log_archives = ''
    if setup_type == 'single':
        force_remove_log_archives = 'yes'
    elif setup_type == 'replica':
        force_remove_log_archives = 'replica'
    else:
        force_remove_log_archives = 'no'
                      
    if not 'log_max_archives' in setup_info:
        setup_info['log_max_archives'] = '40'
    
    for s_item in setup_info['svr_info']:
        f = open(os.path.join(s_item['name'],'cubrid.conf'),'a+')
        f.write(cub_conf_template % (force_remove_log_archives, setup_info['cubrid_port_id'], 
                                     setup_info['max_clients'], setup_info['log_max_archives']))
        f.close()
        
    return True

def generate_broker_conf_file(setup_type, setup_info):
    num_part = setup_info["account"][6:]
    for s_item in setup_info['svr_info']:
        if not 'brokers' in s_item:
            continue
        f = open(os.path.join(s_item['name'],'cubrid_broker.conf'),'a+')
        make_broker_common_conf(f, setup_info, num_part)
            
        for b_info in s_item['brokers']:
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
        
    broker_name = broker_info['name']+'_'+broker_info['mode']
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
ACCESS_CONTROL_FILE     =/home1/%s/CUBRID/conf/broker.access
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
SOURCE_ENV              =/home1/%s/CUBRID/conf/cubrid.env
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
SOURCE_ENV              =/home1/%s/CUBRID/conf/cubrid.env
APPL_SERVER_MAX_SIZE    =70
ACCESS_MODE             =RW    
    """
    fp.write( broker_conf % (setup_info["master_shm_id"], setup_info["account"]))
    fp.write( broker_qe_so_conf % ('20'+num_part+'40', '20'+num_part+'40', setup_info["account"]))
    fp.write( broker_qe_rw_conf % ('20'+num_part+'50', '20'+num_part+'50', setup_info["account"]))

    return True

def is_valid_conf(setup_info):
    acc_str = setup_info['account']
    if acc_str[0:6] != 'cubrid':
        print('[ERR] MUST have \'account\' key')
        return False

    if not 'svc_name' in setup_info:
        print('[ERR] MUST have \'svc_name\' key')
        return False

    recommended_max_clients = get_valid_max_clients(setup_info)+20
    if 'max_clients' in setup_info:
        if int(setup_info['max_clients']) < recommended_max_clients:
            print('[ERR] max_clients MUST be over %s' % str(recommended_max_clients+20))
            return False     
    else:
        setup_info['max_clients'] = str(recommended_max_clients)
    
    for s_item in setup_info['svr_info']:
        if not 'ip' in s_item:
            print('[ERR]: MUST have \'ip\' in '+s_item['name'])
            return False
        if not 'name' in s_item:
            print('[ERR]: MUST have \'name\' in '+s_item['name'])
            return False            
        for b_info in s_item['brokers']:
            if not 'name' in b_info:
                print('[ERR]: MUST have broker \'name\' in '+s_item['name'])
                return False
        for d_info in s_item['databases']:
            if not 'name' in d_info:        
                print('[ERR]: MUST have database \'name\' key in '+s_item['name'])
                return False
       
    return True

# main 
if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Generator for CUBRID conf file')
    parser.add_argument('conf_file_name', metavar='conf_file', type=str, nargs=1,
                        help='a file for CUBRID setup info')
    args = parser.parse_args()

    yaml_file = open(args.conf_file_name[0])
    in_yaml = yaml.load(yaml_file, Loader=yaml.FullLoader)

    if is_valid_conf(in_yaml) == False:
        print('Conf file error')
        exit(0)

    setup_type = get_setup_type(in_yaml)
    
    svc_name = make_setup_dir(in_yaml)
    generate_hosts_file(svc_name, in_yaml)
    generate_broker_conf_file(setup_type, in_yaml)
    generate_cub_conf_file(setup_type, in_yaml)
    generate_access_control_file(in_yaml)
    if setup_type != 'single':
        print('1')