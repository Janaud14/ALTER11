txt = open("index.html", encoding="utf-8").read()
print("{ :", txt.count("{"), "  } :", txt.count("}"))
