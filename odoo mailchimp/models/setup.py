import os
import subprocess
import sys


class Packages:
    """
    This Class installs required Packages or library
    """

    get_pckg = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
    installed_packages = [r.decode().split('==')[0] for r in get_pckg.split()]
    required_packeges= ['mailchimp3']
    for packg in required_packeges:
        if packg in installed_packages:
            pass
        else:
            print('installing package')
            os.system('pip3 install ' + packg)


