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

OptionParser.new do |opts|
  opts.banner = "Usage: ruby #{$0} -s site [options]"
  opts.on("-s", "--site  SITE", "The SITE you want to configure") do |str|
    options[:site] = str
  end
end.parse!

#Missing site name
if options[:site].nil?
  puts "Usage: ruby #{$0} -s site [options] (-h for help)"
  raise OptionParser::MissingArgument
end

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
              kind = port['kind'].nil? ? "node" : "#{port['kind']}"
              uid = port['uid']
              device_port = port['port'].nil? ? "" : "-#{port['port']}"
              begin
                device = "#{uid.nil? ? "None" : "#{site}.#{uid}#{device_port}"}"
                #device = "#{uid.nil? ? "None" : "#{uid}#{device_port}"}"
                switch_port = "#{snmp_pattern.sub("%LINECARD%", l.to_s).sub("%PORT%", p.to_s)}"
                if !uid.nil?
                  $switchs.key?(switch) ? $switchs[switch] << device : $switchs[switch]=[device]
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

#Iteration on each network_equipment of the site
#Define default link to the API
api = RestClient::Resource.new('https://api.grid5000.fr/stable/', :verify_ssl => OpenSSL::SSL::VERIFY_NONE)

#Get cluster information
network_equipments = JSON.parse api["sites/#{options[:site]}/network_equipments"].get(:accept => 'application/json')
parse_cluster(network_equipments, options[:site])

print $switchs
#walk on $switchs to place node probes later
#$switchs.keys.each do |switch|
#  write_probes(options[:site], switch)
#end
