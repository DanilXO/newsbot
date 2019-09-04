import sys

from vk_bot import VkBot
import subprocess

if __name__ == '__main__':
    bot = VkBot()
    sender = subprocess.Popen([sys.executable, "sender.py"])
    bot.run()
    sender.kill()
