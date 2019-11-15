import sys
import os.path
sys.path.append('..')
from vk_bot import VkBot
import subprocess
DEBUG = False
if __name__ == '__main__':
    bot = VkBot()
    sender = subprocess.Popen([sys.executable, "sender.py"])
    bot.run()
    sender.kill()
