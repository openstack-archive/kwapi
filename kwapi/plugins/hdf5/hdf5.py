
LOG = log.getLogger(__name__)


def create_probe_dir(probe):
    """Creates all required directories."""
    probe_dir = cfg.CONF.hdf5_dir +get_host_cluster(probe.split('.')[1])
    try:
       os.makedirs(probe_dir)
    except OSError as exception:
       if exception.errno != errno.EEXIST:
           raise
    return probe_dir            
            
def create_hdf5_file(probe):
    """ """ 
    probe_dir = create_probe_dir(probe)
    f = h5py.File(probe_dir+probe+'.hdf5','w')
    
    f.close()
    
    
    


def update_hdf5(probe, measurements):
    """A method to add data t """
    
    # if not file exists 
    
    # open it
    
    
                