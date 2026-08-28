import pandas as pd

# 确保这里的路径和你训练代码里的一模一样
csv_path = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-TrainMetadata-iNat.csv"

print(f"正在读取文件: {csv_path}")
df = pd.read_csv(csv_path)
print(f"文件总行数: {len(df)}")

# 搜索包含该文件名的行
target = "44177434"
print(f"\n正在搜索文件名包含 '{target}' 的行...")

# 在 image_path 列中搜索
result = df[df['image_path'].astype(str).str.contains(target)]

if not result.empty:
    print("\n✅ 找到了！Python 在这些行里看到了它：")
    print(result[['binomial_name', 'image_path', 'class_id']])
    print(f"\n它在 CSV 的第 {result.index.tolist()} 行 (从0开始计数)")
else:
    print("\n❌ 确实没找到。看来是代码里的逻辑或者文件路径有问题。")
