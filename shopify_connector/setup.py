import os
import subprocess
import sys


class Packages:
    """
    Install Required Packages
    """
    get_pckg = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
    installed_packages = [r.decode().split('==')[0] for r in get_pckg.split()]
    required_packeges = ['shopifyAPI']
    for packg in required_packeges:
        if packg in installed_packages:
            pass
        else:
            print('installing package')
            os.system('pip install ' + packg)