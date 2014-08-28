#!/usr/bin/env ruby
# == Synopsis
#
# Retrieve cluster of a site and their nodes with the API. 
# Request each node to retrieve switch address and OIDs.
#
# == Usage
#
# ruby configure-driver.rb 
#
# == Author
# Clement Parisot, Loria - Algorille, Nancy

require 'pp'
require 'rest_client'
require 'json'
require 'snmp'
require 'resolv'
include SNMP
require 'optparse'
require 'socket'

hostname = Socket.gethostname
node_uid, site_uid, grid_uid, ltd = hostname.split(".")

options = {
  site:	site_uid,
}

$switchs = {}

#Missing site name
if options[:site].nil?
  puts "Usage: ruby #{$0} -s site [options] (-h for help)"
  raise OptionParser::MissingArgument
end

#Print the header
def header(options)
  puts "FQDNLookup true
LoadPlugin syslog
<Plugin syslog>
        LogLevel info
</Plugin>
#LoadPlugin battery
#LoadPlugin cpu
#LoadPlugin df
#LoadPlugin disk
#LoadPlugin entropy
#LoadPlugin interface
#LoadPlugin irq
#LoadPlugin load
#LoadPlugin memory
#LoadPlugin processes
LoadPlugin rrdtool
LoadPlugin snmp
#LoadPlugin swap
#LoadPlugin users
<Plugin rrdtool>
        DataDir \"/var/lib/collectd/rrd\"
</Plugin>
<Plugin snmp>
        <Data \"std_traffic\">
                Type \"if_octets\"
                Table true
                InstancePrefix \"traffic\"
                Instance \"IF-MIB::ifDescr\"
                Values \"IF-MIB::ifHCInOctets\" \"IF-MIB::ifHCOutOctets\"
        </Data>"
end

header(options)

#Parse the cluster file to extract nodes uids
def parse_cluster(d, site)
  d['items'].each do |item|
    if item['type'] == "network_equipment"
      switch = item['uid']
      l = -1
      item['linecards'].each do |linecard|
        l+=1
        snmp_pattern = linecard['snmp_pattern']
        if snmp_pattern.nil?
          $stderr.puts "No pattern for #{switch}:#{l}"
        else
          p = -1
          ports = linecard['ports']
          if !ports.nil? 
            ports.each do |port|
              p+=1
              uid = port['uid']
              device_port = port['port'].nil? ? "" : "-#{port['port']}"
              begin
                device = "#{uid.nil? ? "None" : "#{uid}#{device_port}_#{switch}"}"
                switch_port = "#{snmp_pattern.sub("%LINECARD%", l.to_s).sub("%PORT%", p.to_s)}"
                if !uid.nil?
                  $switchs.key?(switch) ? $switchs[switch][switch_port]=device : $switchs[switch]={switch_port=>device}
                end
              rescue
                $stderr.puts "Can't write #{switch}:#{snmp_pattern}:#{l}:#{p}:#{uid} : #{$!}" 
              end
            end
          end
        end
      end
    end
  end
end

#SNMP Requests to find the correct OID
def write_probes(site,switch)
  if switch == "" || switch.nil?
    return
  end
  switch_addr = Resolv.getaddress switch+".#{site}.grid5000.fr"
  probes = []
  begin
    SNMP::Manager.open(:host => switch_addr) do |manager|
      manager.walk(["ifDescr"]) do |(ifDescr)|
        node = $switchs[switch][ifDescr.value]
        probes << node
      end
    end
  rescue
    return
  end
  #Erase last 'None' values
  probes.pop until !probes[-1].nil?
  if probes.length == 0 #no probes on switch
    return
  end
  probes.each do |probe|
    if !probe.nil?
      printf "<Data \"std_traffic_%s\">\n", probe
      printf "\tType \"if_octets\"\n"
      printf "\tTable false\n"
      printf "\tInstance \"%s\"\n", probe
      printf "\tValues \"IF-MIB::ifHCInOctets.%d\" \"IF-MIB::ifHCOutOctets.%d\"\n", probes.index(probe)+1, probes.index(probe)+1
      printf "</Data>\n"
      printf "<Host \"%s\">\n", probe
      printf "\tAddress \"%s.%s.grid5000.fr\"\n", switch, site
      printf "\tVersion 2\n"
      printf "\tCommunity \"public\"\n"
      printf "\tCollect \"std_traffic_%s\"\n", probe
      printf "</Host>\n"
    end
  end
end

#Iteration on each network_equipment of the site
#Define default link to the API
api = RestClient::Resource.new('https://api.grid5000.fr/stable/', :verify_ssl => OpenSSL::SSL::VERIFY_NONE)

#Get cluster information
network_equipments = JSON.parse api["sites/#{options[:site]}/network_equipments"].get(:accept => 'application/json')
parse_cluster(network_equipments, options[:site])

#walk on $switchs to place node probes later
$switchs.keys.each do |switch|
  write_probes(options[:site], switch)
end
puts "</Plugin>\n"
