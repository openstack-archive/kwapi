import json
import numpy
import sys


def help():
    print 'Usage:\n\t' + sys.argv[0] + ' file'
    exit()

if len(sys.argv) != 2:
    help()

try:
    json_data = open(sys.argv[1])
except IOError:
    help()
data = json.load(json_data)

print 'Node'.ljust(20) + 'Min'.ljust(10) + 'Max'.ljust(10) + 'Avg'.ljust(10) + 'Std'.ljust(10)
for item in data['items']:
    if len(item['values']) == 1 and item['values'][0] == 'Unknown probe':
        print item['uid'].ljust(20) + '-'.ljust(10) + '-'.ljust(10) + '-'.ljust(10) + '-'.ljust(10)
    else:
        print item['uid'].ljust(20) + str(round(min(item['values']), 2)).ljust(10) + \
                str(max(item['values'])).ljust(10) + \
                str(round(numpy.average(item['values']), 2)).ljust(10) + \
                str(round(numpy.std(item['values']), 2)).ljust(10)
