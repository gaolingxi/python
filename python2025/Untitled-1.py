#%%
str8 = input("Enter your name")  #在Python中，input()函数用于接收用户输入。等待用户输入一些文本。用户输入的文本在按下回车键后会被赋值给变量 str8。
print("Welcome to Hangzhou Normal University",str8)






# %%
str8 = input("Enter your name")  #在Python中，input()函数用于接收用户输入。等待用户输入一些文本。用户输入的文本在按下回车键后会被赋值给变量 str8。
print("Welcome to Hangzhou Normal University",str8)
# %%
import numpy as np
import matplotlib.pyplot as plt

#%%
# 定义螺旋的角度和半径
t = np.linspace(0, 2 * np.pi, 1000)
r = np.linspace(0, 1, 1000)
x = r * np.cos(t)
y = r * np.sin(t)

#%%

# 创建颜色映射
colors = np.sqrt(x**2 + y**2)


#%%
# 创建图形
plt.figure(figsize=(8, 8))

#%%
plt.pcolor(x, y, colors, shading='gouraud', cmap='viridis')

#%%
plt.axis('equal')  # 确保x和y轴的比例相同
plt.axis('off')  # 关闭坐标轴

# 显示图形
plt.show()
# %%
