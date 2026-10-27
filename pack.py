import os, shutil, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
REL = os.path.join(ROOT, "release")
PKG = os.path.join(REL, "QMYZ-v1.0.0-portable")
DIST = os.path.join(ROOT, "dist", "QMYZ")

if os.path.isdir(PKG):
    shutil.rmtree(PKG)
shutil.copytree(DIST, PKG)

shutil.copy2(os.path.join(ROOT, "app", "LICENSE.txt"), os.path.join(PKG, "LICENSE.txt"))
for name in ["使用说明.txt", "源码获取说明.txt"]:
    shutil.copy2(os.path.join(ROOT, "docs", name), os.path.join(PKG, name))

src = os.path.join(PKG, "source")
os.makedirs(src, exist_ok=True)
shutil.copy2(os.path.join(ROOT, "app", "gui.py"), os.path.join(src, "gui.py"))
shutil.copy2(os.path.join(ROOT, "qmyz.spec"), os.path.join(src, "qmyz.spec"))

zip_path = os.path.join(REL, "QMYZ-v1.0.0-portable.zip")
if os.path.exists(zip_path):
    os.remove(zip_path)
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for base, dirs, files in os.walk(PKG):
        for f in files:
            full = os.path.join(base, f)
            arc = os.path.relpath(full, REL)
            z.write(full, arc)

print("pkg files:", sum(len(f) for _, _, f in os.walk(PKG)))
print("zip MB: %.1f" % (os.path.getsize(zip_path) / 1048576))
