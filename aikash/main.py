from threading import Thread
from tree_model import Tree, Context
from webserv import WEBkash
from ai_model import AIkash

# ai_model = AIkash(device="cuda")
ai_model = AIkash()

tree_model = Tree(def_response=ai_model.work)
web_model = WEBkash(tree=tree_model, def_response=ai_model.work)


tre = Thread(target=tree_model.cycle).start()
serv = Thread(target=web_model.run).start()


