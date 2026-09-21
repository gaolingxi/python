#%%
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import fsolve

# 参数设置
beta = 0.96  # 折现因子
r = 0.04     # 利率
w = 1.0      # 工资率
b = 0.1      # 最大借款额度
grid_size = 100  # 网格大小
grid = np.linspace(0, 10, grid_size)  # 资产网格

# 效用函数
def u(c):
    return np.log(c)

# 预算约束
def budget(a, c, z):
    return c + a[1] == w * z + (1 + r) * a[0]

# 价值函数
def v(a, z):
    c = budget(a, a[1], z)
    return u(c)

# 初始化条件
a0 = np.zeros(grid_size)
a_next = np.zeros(grid_size)

# Bewley模型方程
def Bewley_model(a):
    for i in range(grid_size):
        for j in range(grid_size):
            if grid[j] > grid[i] and a[j] - a[i] <= b:
                a_next[i] = a[j]  # 这里应该是一个方程，但为了示例，我们简化了逻辑
    return a_next - a0
#%%
# 求解方程
a_star = fsolve(Bewley_model, a0)

# 绘制结果
plt.plot(grid, a_star, label='Optimal Savings')
plt.xlabel('Current Assets')
plt.ylabel('Next Period Assets')
plt.title('Optimal Savings Decisions in Bewley Model')
plt.legend()
plt.grid(True)
plt.show()
# %%
