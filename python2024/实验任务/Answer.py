#%%
rate = int(input("请您为《唐朝诡事录》进行评分(只能输入数字1~9)"))
print(rate*"A")


# %%
# 定义国家名称
country = "中国"

# 定义GDP，以万亿美元为单位
gdp = 14.34

# 定义增长率
growth_rate = 0.061  # 6.1%

# 使用format()函数格式化字符串
report = "国家: {0}\nGDP(万亿美元): {1:,.2f}\n增长率: {2:.2%}".format(country, gdp, growth_rate)
print(report)


# 设置三角形的高度
height = 5

# 使用for循环生成三角形
for i in range(height):
    # 打印空格
    print(" " * (height - i- 1), end="")
    # 打印星号
    print("*" * (2*i + 1))

#%%
# 定义三角形的高度
height = 5

# 使用嵌套for循环生成三角形
for i in range(height):
    # 打印空格
    for j in range(height - i - 1):
        print(" ", end="")
    # 打印星号
    for k in range(2 * i + 1):
        print("*", end="")
    # 换行
    print()



# 实验四
# 中文月份列表
#%%
chinese_months = [
    "一月", "二月", "三月", "四月", "五月", "六月",
    "七月", "八月", "九月", "十月", "十一月", "十二月"
]

# 英文月份列表
english_months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# 用户输入中文月份
chinese_month = input("请输入中文月份：")

# 查找对应的英文月份
def get_english_month(chinese_month):
    try:
        index = chinese_months.index(chinese_month)
        return english_months[index]
    except ValueError:
        return "未知月份"

# 输出对应的英文月份
english_month = get_english_month(chinese_month)
print(f"对应的英文月份是：{english_month}")





# %%
# 计算等间距网格点
b = 2
a = 0
n = 500
h = (b - a) / n
points = [a + i * h for i in range(n + 1)]
print(points)
# %%
values = [x**2 for x in points]
# %%
x =1.5
for i in range(n + 1):
        if a <= x <= points[i]:
            if i == 0 or i == n:
                # 如果x是端点，直接返回端点的函数值
                y_hat = values[i]
            else:
                # 进行线性插值
                p1 = points[i - 1]
                v1 = values[i - 1]
                p2 = points[i]
                v2 = values[i]
                y_hat =  v1 + (v2 - v1) * (x - p1) / (p2 - p1)
            print(y_hat)   
# %%
# 定义一个3x4矩阵
matrix_a = [
    [1, 2, 3, 4],
    [5, 6, 7, 8],
    [9, 10, 11, 12]
]

# 定义一个4x3矩阵
matrix_b = [
    [13, 14, 15],
    [16, 17, 18],
    [19, 20, 21],
    [22, 23, 24]
]

# 初始化结果矩阵为一个3x3的零矩阵
result = [[0 for _ in range(3)] for _ in range(3)]

# 计算结果矩阵
for i in range(3):  # 遍历matrix_a的行
    for j in range(3):  # 遍历matrix_b的列
        for k in range(4):  # 遍历matrix_a的列和matrix_b的行
            result[i][j] += matrix_a[i][k] * matrix_b[k][j]

# 打印结果矩阵
for row in result:
    print(row)



#%%
key_value_pairs = [
    ('a', 1),
    ('b', 2),
    ('a', 3),
    ('c', 4),
    ('b', 5),
    ('a', 6)
]

# 创建一个空字典来存储分组后的键值对
grouped_dict = {}

# 遍历键值对列表
for key, value in key_value_pairs:
    # 如果键已经在字典中，将值追加到对应的列表中
    if key in grouped_dict:
        grouped_dict[key].append(value)
    # 如果键不在字典中，创建一个新的列表，并将值添加进去
    else:
        grouped_dict[key] = [value]

# 打印结果
print(grouped_dict)
# %%
# Define a function 'list_of_dicts' that splits a dictionary of lists into a list of dictionaries.
def list_of_dicts(marks):
    # Get the keys (subjects) from the 'marks' dictionary.
    keys = marks.keys()
    	
    # Use the 'zip' function to transpose the lists of marks into tuples.
    vals = zip(*[marks[k] for k in keys])
    
    # Create a list of dictionaries by zipping the keys and the transposed tuples.
    result = [dict(zip(keys, v)) for v in vals]
    return result

# Create a dictionary 'marks' with subjects as keys and lists of marks as values.
marks = {'Science': [88, 89, 62, 95], 'Language': [77, 78, 84, 80]}

# Print a message indicating the start of the code section and the original dictionary of lists.
print("Original dictionary of lists:")
print(marks)

# Print a message indicating the intention to split the dictionary of lists into a list of dictionaries.
print("\nSplit said dictionary of lists into a list of dictionaries:")

# Call the 'list_of_dicts' function to split the dictionary of lists and print the resulting list of dictionaries.
print(list_of_dicts(marks)) 

# %%
economic_indicators = {
    'GDP_Growth_Rate': [2.5, 2.7, 3.1, 2.9],
    'Unemployment_Rate': [5.0, 4.8, 4.7, 4.9],
    'Inflation_Rate': [1.8, 1.9, 2.1, 2.0],
    'Public_Debt_to_GDP': [70.5, 70.2, 71.5, 72.0]
}

# 使用列表推导式和zip函数将字典转换为列表形式的字典
economic_data_list = [
    {'GDP_Growth_Rate': gdp, 'Unemployment_Rate': unemployment, 'Inflation_Rate': inflation, 'Public_Debt_to_GDP': debt}
    for gdp, unemployment, inflation, debt in zip(
        economic_indicators['GDP_Growth_Rate'], 
        economic_indicators['Unemployment_Rate'], 
        economic_indicators['Inflation_Rate'], 
        economic_indicators['Public_Debt_to_GDP']
    )
]

print(economic_data_list)
# %%
