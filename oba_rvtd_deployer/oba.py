from fabric.api import env, run


class ObaRvtdFab:
    
    def __init__(self, host_name, user, key_filename):
        env.host_string = host_name
        env.user = user
        env.key_filename = key_filename
        
    def test_cmd(self):
        run('ll')
            
    
def start():
    '''Start the OBA server on the EC2 instance.
    '''
    pass


def stop():
    '''Stop the OBA server on the EC2 instance.
    '''
    pass
