require 'pp'
require 'rest_client'
require 'json'
 
#RestClient.log = 'stdout'
api = RestClient::Resource.new('https://api.grid5000.fr:443/')

puts "---- Getting sites"
sites = JSON.parse api['/3.0/sites'].get(:accept => 'application/json')
File::open("sites.json", "w") { |fd| fd.puts JSON::pretty_generate(sites) }
ne = JSON.parse api['/3.0/network_equipments'].get(:accept => 'application/json')
File::open("network_equipments.json", "w") { |fd| fd.puts JSON::pretty_generate(ne) }
sites['items'].each do |site|
  puts "---- Getting network_equipments for #{site['uid']}"
  lne = site['links'].select { |e| e['rel'] == 'network_equipments' }[0]['href']
  ne = JSON.parse api[lne].get(:accept => 'application/json')
  File::open("#{site['uid']}-network_equipments.json", "w") { |fd| fd.puts JSON::pretty_generate(ne) }

  puts "---- Getting clusters for #{site['uid']}"
  lc = site['links'].select { |e| e['rel'] == 'clusters' }[0]['href']
  cl = JSON.parse api[lc].get(:accept => 'application/json')
  File::open("#{site['uid']}-clusters.json", "w") { |fd| fd.puts JSON::pretty_generate(cl) }

  cl['items'].each do |cluster|
    puts "---- Getting #{cluster['uid']}"
    ln = cluster['links'].select { |e| e['rel'] == 'nodes' }[0]['href']
    nodes = JSON.parse api[ln].get(:accept => 'application/json')
    File::open("#{site['uid']}-cluster-#{cluster['uid']}.json", "w") { |fd| fd.puts JSON::pretty_generate(nodes) }
  end

  puts "---- Getting pdus for #{site['uid']}"
  lc = site['links'].select { |e| e['rel'] == 'pdus' }
  if not lc.empty?
    lc = lc[0]['href']
    cl = JSON.parse api[lc].get(:accept => 'application/json')
    File::open("#{site['uid']}-pdus.json", "w") { |fd| fd.puts JSON::pretty_generate(cl) }
  end
end
