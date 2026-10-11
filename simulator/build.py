import os
d = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(d, "template.html"), encoding="utf-8").read()
solver = open(os.path.join(d, "solver.js"), encoding="utf-8").read()
assert "/*__SOLVER__*/" in tpl
out = tpl.replace("/*__SOLVER__*/", solver)
open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(out)
# extract script for syntax check
s = out.index("<script>") + len("<script>")
e = out.index("</script>")
open(os.path.join(d, "app.js"), "w", encoding="utf-8").write(out[s:e])
print("built", len(out), "bytes")
