import os
import pandas as pd
import torch
import open_clip
from torch import nn
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from tqdm import tqdm

# ================= 配置区域 =================
# 1. 图片文件夹 (验证集图片应该也在这里)
DATA_PATH = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-large_size"

# 2. 训练集 CSV (必须读这个来获取蛇的 ID 顺序)
TRAIN_CSV = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-TrainMetadata-iNat.csv"

# 3. 验证集 CSV (这是考卷)
VAL_CSV = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-ValMetadata.csv"

# 4. 刚才训练好的第 10 轮模型权重
MODEL_PATH = "bioclip2_snake_epoch_10.pth"

# 显存够的话，验证时 Batch Size 可以大一点
BATCH_SIZE = 64


# ===========================================

class SnakeDataset(Dataset):
    def __init__(self, csv_file, root_dir, species_to_idx, transform=None):
        self.annotations = pd.read_csv(csv_file)
        self.root_dir = root_dir
        self.transform = transform
        self.species_to_idx = species_to_idx

        # 过滤掉验证集中出现、但训练集中没见过的蛇 (防止报错)
        initial_len = len(self.annotations)
        self.annotations = self.annotations[self.annotations['binomial_name'].isin(species_to_idx.keys())]
        print(f"加载验证集: 原有 {initial_len} 张，有效 {len(self.annotations)} 张")

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, index):
        rel_path = self.annotations.iloc[index]['image_path']
        img_path = os.path.join(self.root_dir, rel_path)
        species_name = self.annotations.iloc[index]['binomial_name']
        label_idx = self.species_to_idx[species_name]

        try:
            image = Image.open(img_path).convert("RGB")
            if self.transform:
                image = self.transform(image)
        except:
            # 如果图片坏了，返回全黑图
            image = torch.zeros((3, 224, 224))

        return image, label_idx


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"正在使用设备: {device} 进行验证...")

    # 1. 必须先读取训练集 CSV，建立完全一样的“蛇名字典”
    print("正在重建类别映射...")
    train_df = pd.read_csv(TRAIN_CSV)
    species_list = sorted(train_df['binomial_name'].unique().tolist())
    species_to_idx = {name: idx for idx, name in enumerate(species_list)}
    num_classes = len(species_list)
    print(f"类别数量: {num_classes}")

    # 2. 加载 BioCLIP 2 模型架构
    print("正在加载 BioCLIP 2 (ViT-L/14)...")
    model, _, preprocess_val = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
    model.to(device)
    model.eval()  # 开启评估模式

    # 3. 定义分类头 (768维)
    classification_head = nn.Linear(768, num_classes).to(device)

    # 4. 加载你训练好的权重
    if os.path.exists(MODEL_PATH):
        print(f"正在加载权重文件: {MODEL_PATH}")
        classification_head.load_state_dict(torch.load(MODEL_PATH))
        classification_head.eval()  # 开启评估模式
    else:
        print(f"错误: 找不到模型文件 {MODEL_PATH}")
        return

    # 5. 准备验证数据
    val_dataset = SnakeDataset(VAL_CSV, DATA_PATH, species_to_idx, transform=preprocess_val)
    val_dataloader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=4)

    # 6. 开始考试
    print("开始验证 (Evaluation)...")

    correct = 0
    total = 0

    with torch.no_grad():
        for images, labels in tqdm(val_dataloader):
            images = images.to(device)
            labels = labels.to(device)

            # 提取特征
            image_features = model.encode_image(images)
            image_features /= image_features.norm(dim=-1, keepdim=True)

            # 预测
            outputs = classification_head(image_features.float())

            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    acc = 100 * correct / total
    print(f"========================================")
    print(f"验证集最终准确率: {acc:.2f}%")
    print(f"========================================")


if __name__ == "__main__":
    main()
