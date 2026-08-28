import os
import pandas as pd
import torch
import open_clip
from torch import nn, optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image, ImageFile
from tqdm import tqdm

# 防止某些图片截断导致报错
ImageFile.LOAD_TRUNCATED_IMAGES = True

# ================= 配置区域 =================
# 请确保路径正确
DATA_PATH = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-large_size"
CSV_PATH = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-TrainMetadata-iNat.csv"

# 权重保存/加载路径
BEST_MODEL_PATH = "bioclip2_snake_best.pth"
LAST_MODEL_PATH = "bioclip2_snake_last.pth"

# 训练设置
START_EPOCH = 10  # 你想从第几轮开始显示
END_EPOCH = 30  # 总共跑多少轮
BATCH_SIZE = 256
LEARNING_RATE = 1e-3
NUM_WORKERS = 8  # 根据你的CPU核心数调整，通常设置为 4-8


# ===========================================

class SnakeDataset(Dataset):
    def __init__(self, csv_file, root_dir, transform=None):
        print(f"📖 正在读取 CSV 文件: {csv_file} ...")
        df = pd.read_csv(csv_file)
        self.root_dir = root_dir
        self.transform = transform

        # === 核心修复：过滤掉不存在的图片 ===
        print("🔍 正在检查文件完整性 (这可能需要 1-2 分钟)...")
        valid_indices = []
        # 使用 tqdm 显示进度
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Filtering Images"):
            # 拼接完整路径
            full_path = os.path.join(root_dir, row['image_path'])
            if os.path.exists(full_path):
                valid_indices.append(idx)

        # 只保留存在的文件
        self.annotations = df.iloc[valid_indices].reset_index(drop=True)
        print(f"✅ 过滤完成！")
        print(f"   - 原始数量: {len(df)}")
        print(f"   - 有效数量: {len(self.annotations)}")
        print(f"   - 剔除缺失: {len(df) - len(self.annotations)} (这些就是导致你之前准确率低的原因)")
        # ====================================

        self.species_list = sorted(self.annotations['binomial_name'].unique().tolist())
        self.species_to_idx = {name: idx for idx, name in enumerate(self.species_list)}

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, index):
        rel_path = self.annotations.iloc[index]['image_path']
        img_path = os.path.join(self.root_dir, rel_path)
        species_name = self.annotations.iloc[index]['binomial_name']
        label_idx = self.species_to_idx[species_name]

        image = Image.open(img_path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        return image, label_idx


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"⚙️ 使用设备: {device}")

    # 1. 加载 BioCLIP 2
    print("🧠 正在加载 BioCLIP 2 模型...")
    model, preprocess_train, _ = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
    model.to(device)

    for param in model.parameters():
        param.requires_grad = False
    print("🔒 已冻结 BioCLIP 主干网络，仅训练分类头。")

    # 3. 数据集
    dataset = SnakeDataset(csv_file=CSV_PATH, root_dir=DATA_PATH, transform=preprocess_train)
    dataloader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
        pin_memory=True,
        persistent_workers=True  # 加速数据读取
    )

    # 4. 分类头
    num_classes = len(dataset.species_list)
    print(f"📊 分类类别数: {num_classes}")
    classification_head = nn.Linear(768, num_classes).to(device)

    # 5. 优化器与 Loss
    optimizer = optim.AdamW(classification_head.parameters(), lr=LEARNING_RATE)
    criterion = nn.CrossEntropyLoss()

    # === 新增：学习率调度器 (Cosine Annealing) ===
    # 这会让学习率随着训练逐渐下降，帮助模型收敛到更低的 Loss
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=END_EPOCH - START_EPOCH)

    # 6. 加载权重逻辑
    best_loss = 2.28  # 你的基准 Loss

    # 优先加载 "Last" (断点续传)，如果没有则加载 "Best"，都没有则从头开始
    if os.path.exists(LAST_MODEL_PATH):
        print(f"🔄 发现上次中断的训练权重 ({LAST_MODEL_PATH})，正在加载...")
        classification_head.load_state_dict(torch.load(LAST_MODEL_PATH))
    elif os.path.exists(BEST_MODEL_PATH):
        print(f"🔄 加载历史最佳权重 ({BEST_MODEL_PATH})，继续优化...")
        classification_head.load_state_dict(torch.load(BEST_MODEL_PATH))
    else:
        print("⚠️ 未找到预训练权重，将从头开始训练分类头。")

    print(f"🚀 开始训练: Epoch {START_EPOCH + 1} -> {END_EPOCH}")
    print(f"🎯 当前挑战的最佳 Loss 基准: {best_loss}")

    for epoch in range(START_EPOCH, END_EPOCH):
        model.eval()  # Backbone 始终 Eval
        classification_head.train()  # Head 始终 Train

        total_loss = 0
        correct = 0
        total = 0

        progress_bar = tqdm(dataloader, desc=f"Epoch {epoch + 1}/{END_EPOCH}")

        for images, labels in progress_bar:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()

            with torch.no_grad():
                # 提取特征
                image_features = model.encode_image(images)
                image_features /= image_features.norm(dim=-1, keepdim=True)

            # 分类
            outputs = classification_head(image_features.float())
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()

            # 统计
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

            # 实时更新进度条
            current_loss = total_loss / (progress_bar.n + 1)
            current_acc = 100 * correct / total
            current_lr = optimizer.param_groups[0]['lr']
            progress_bar.set_postfix({
                'Loss': f"{current_loss:.4f}",
                'Acc': f"{current_acc:.2f}%",
                'LR': f"{current_lr:.1e}"
            })

        # === Epoch 结束处理 ===
        epoch_avg_loss = total_loss / len(dataloader)

        # 更新学习率
        scheduler.step()

        # 1. 保存最新模型 (防止断电白跑)
        torch.save(classification_head.state_dict(), LAST_MODEL_PATH)

        # 2. 保存最佳模型
        if epoch_avg_loss < best_loss:
            print(f"\n🏆 新纪录！Loss 从 {best_loss:.4f} 降到了 {epoch_avg_loss:.4f}")
            best_loss = epoch_avg_loss
            torch.save(classification_head.state_dict(), BEST_MODEL_PATH)
            print(f"💾 已保存最佳模型: {BEST_MODEL_PATH}")
        else:
            print(f"\n📉 本轮 Loss {epoch_avg_loss:.4f} 未打破纪录 ({best_loss:.4f})")


if __name__ == "__main__":
    main()
