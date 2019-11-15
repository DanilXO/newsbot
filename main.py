import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

DEBUG = False
if __name__ == '__main__':
    from vk_bot import VkBot
    import subprocess
    bot = VkBot()
    sender = subprocess.Popen([sys.executable, "sender.py"])
    bot.run()
    sender.kill()
