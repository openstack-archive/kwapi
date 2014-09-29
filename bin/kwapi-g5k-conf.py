#!/usr/bin/env python
# This file is part of kwapi-g5k
# 
# It allows to configure automatically the probes using the reference API
#


from socket import getfqdn
from pprint import pprint
from execo import Process, logger
from execo_g5k import get_site_clusters, get_cluster_hosts, get_host_attributes, get_resource_attributes


_community = 'public'
_protocol = '2c'

# Determining site
site = getfqdn().split('.')[1]
# site = 'lyon'

logger.info('Generating configuration of kwapi-drivers for %s',
            site)

logger.info('Retrieving monitoring equipments information')
equips = {}
for pdu in get_resource_attributes('/sites/'+site+'/pdus/')['items']:
    if pdu.has_key('sensors'):
        for sensor in pdu['sensors']:
            if sensor.has_key('power'):
                if 'snmp' in sensor['power']:
                    if sensor['power']['per_outlets']:
                        oid = sensor['power']['snmp']['outlet_prefix_oid']
                    else:
                        oid = sensor['power']['snmp']['total_oids'][0][0:-2]
                    equips[pdu['uid']] = {'driver': 'Snmp', 'parameters': 
                        {'community': _community, 'protocol': '1',
                         'ip': pdu['uid'] + '.' + site + '.grid5000.fr',
                         'oid': oid }, 'mapping': [], 'probes': []}
                if 'wattmetre' in sensor['power']:
                    equips[pdu['uid']] = {'driver': 'Json_url', 'parameters': 
                        {'url': sensor['power']['wattmetre']['www']['url']},
                                        'probes': []}

logger.info('Retrieving network equipments information')
switchs = {}
for network_equipment in get_resource_attributes('/sites/'+site+'/network_equipments/')['items']:
    if network_equipment.has_key('type'):
        if network_equipment['type'] == 'network_equipment':
            if network_equipment.has_key('uid'):
                switch = network_equipment['uid']
                l = -1
                if network_equipment.has_key('linecards'):
                    for linecard in network_equipment['linecards']:
                        l+=1
                        snmp_pattern = None
                        if linecard.has_key('snmp_pattern'):
                            snmp_pattern = linecard['snmp_pattern']
                        else:
                            logger.warn("No snmp_pattern for %s: %s" % (switch, l))
                            #break
                        p = -1
                        if linecard.has_key('ports'):
                            ports = linecard['ports']
                            for port in ports:
                                p+=1
                                uid = None
                                device_port = ""
                                if port.has_key('uid'):
                                    uid = port['uid']
                                    if port.has_key('port'):
                                        device_port = '-' + port['port']
                                try:
                                    device = uid + device_port if uid else None
                                    #switch_port = snmp_pattern.replace('%LINECARD%', str(l)).replace('%PORT%', str(p))
                                    #if uid:
                                    if switchs.has_key(switch):
                                        switchs[switch].append(device)
                                    else:
                                        switchs[switch] = [device]
                                except:
                                    logger.error("Can't write %s:%s:%d:%d:%s" % (switch, snmp_pattern, l, p, uid))
pprint(switchs)
#pprint(equips)                            
       
logger.info('Retrieving hosts plug mapping')
for cluster in get_site_clusters(site):
    nodes = get_resource_attributes('/sites/' + site + '/clusters/' + cluster + \
                                    '/nodes')['items']
    for node in nodes:
        if not node.has_key('sensors'):
            print node['uid']
            continue
        power = node['sensors']['power']
        
        if power['available']:
            if 'pdu' in power['via']:               
                if isinstance(power['via']['pdu'], list): 
                    for pdu in power['via']['pdu']:
                        if 'port' in pdu:     
                            equips[pdu['uid'].split('.')[0]]['mapping'].append((node['uid'], pdu['port']))
                        else:
                            if pdu['uid'] is None:
                                print power
                            else:
                                equips[pdu['uid'].split('.')[0]]['mapping'].append((node['uid'], 0))
                else:
                    pdu = power['via']['pdu']
                    if 'port' in pdu:
                        logger.warning('node ' + node['uid'] + ' has str instead of list for power[\'via\']')     
                        equips[pdu['uid'].split('.')[0]]['mapping'].append((node['uid'], pdu['port']))
                    else:
                        equips[pdu['uid'].split('.')[0]]['mapping'].append((node['uid'], 0))
            if 'www' in power['via']:
                if not 'per_outlets' in power or power['per_outlets']:  
                    equips[pdu['uid']]['probes'].append(node['uid'])


# pprint(equips)    
logger.info('Generating probe list for Snmp drivers') 
for equip in equips.itervalues():
    if 'mapping' in equip and len(equip['mapping']) > 0:
        if len(filter(lambda x: x[1] != 0, equip['mapping'])) > 0:
            equip['mapping'] = sorted(equip['mapping'], key=lambda x: x[1])
            equip['probes'] = [None] * equip['mapping'][-1][1]        
            for probe, outlet in equip['mapping']:
                equip['probes'][outlet-1] = probe
        else:
            cluster = equip['mapping'][0][0].split('-')[0]
            radicals = map(lambda x: int(x[0].split('-')[1]), equip['mapping'])
            equip['probes'].append(cluster + '-' + '-'.join(map(str, sorted(radicals))))

network_probes = {}
for switch in switchs:
    #Exclude some switchs
    if switch.endswith("ib") or switch in ["", None]:
        logger.warn("Ignore switch: %s" % switch)
    else:
        switch_addr = "%s.%s.grid5000.fr" % (switch, site)
        probesIN = []
        probesOUT = []
        for node in switchs[switch]:
            if node:
                probesIN.append("%s.%s_%s" % (site, switch, node))
                probesOUT.append("%s.%s_%s" % (site, node, switch))
            else:
                probesIN.append(None)
                probesOUT.append(None)
        #Erase last None values 
        while not probesIN[-1]:
            probesIN.pop()
        while not probesOUT[-1]:
            probesOUT.pop()
        if len(probesIN) == 0 or len(probesOUT) == 0:
            logger.warn("No probes on switch %s" % switch)
            continue
        else:
            network_probes[switch] = {'in':probesIN,
                                      'out':probesOUT,}

# pprint(equips)    

logger.info('Writing new configuration file')
f = open('/tmp/kwapi-drivers-list.conf', 'w')
for equip, data in equips.iteritems():
    if 'probes' in data and data['probes']:
        sec = "\n["+equip+"]\n"
        sec += "probes = ["
        for probe in data['probes']:
            if probe:
                sec += "'" + site + '.' + probe +"'"
            else:
                sec += str(None)
            sec += ", "
        sec += "]\n"
        sec += "driver = "+data['driver']+"\n"
        sec += "data_type = {'name':'power', 'type':'Gauge', 'unit':'W'}\n"
        sec += "parameters = "+str(data['parameters']) + "\n"
        f.write(sec)

OID_IN = "1.3.6.1.2.1.31.1.1.1.6"
OID_OUT = "1.3.6.1.2.1."

for switch in network_probes:
    sec = "\n[%s-IN]\n" % switch
    sec += "probes = ["
    for probe in switch['in']:
        if probe:
            sec += "'" + probe + "'"
        else:
            sec += str(None)
        sec += ", "
    sec += "]\n"
    sec += "driver = Snmp"
    sec += "data_type = {'name':'switch.port.receive.bytes', 'type':'Cumulative', 'unit':'B'}\n"
    sec += "parameters = 'protocol':"+_protocol+
    
f.close()


logger.info('Adding drivers from API to /etc/kwapi/drivers.conf')
bak_conf = Process('[ -f /etc/kwapi/drivers.conf.orig ] && cp /etc/kwapi/drivers.conf.orig /etc/kwapi/drivers.conf || cp /etc/kwapi/drivers.conf /etc/kwapi/drivers.conf.orig')
bak_conf.shell = True
bak_conf.run()
cat_conf = Process('cat /tmp/kwapi-drivers-list.conf >> /etc/kwapi/drivers.conf ; rm /tmp/kwapi-drivers-list.conf')
cat_conf.shell = True
cat_conf.run()

logger.info('Done')
