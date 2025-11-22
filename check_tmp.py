import os

tmp_dir = 'd:/VideoRobot2/tmp'
print('目录是否存在:', os.path.exists(tmp_dir))
if os.path.exists(tmp_dir):
    print('目录内容:', os.listdir(tmp_dir))
else:
    print('目录不存在')