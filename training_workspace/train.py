import os
import sys
import random
import platform
import pandas as pd
import torch
import open_clip
import numpy as np
from torch import nn, optim
from torch.utils.data import Dataset, DataLoader, random_split
from PIL import Image, ImageFile
from tqdm import tqdm
import json
from datetime import datetime
from torch.optim.lr_scheduler import CosineAnnealingLR
import warnings

# 防止截断的大图报错
ImageFile.LOAD_TRUNCATED_IMAGES = True
warnings.filterwarnings('ignore')

# ================= 配置区域 =================
# 根据你的环境路径配置
DATA_PATH = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-large_size"
TRAIN_CSV = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-TrainMetadata-iNat.csv"
VAL_CSV = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-ValMetadata.csv"

# 训练参数
START_EPOCH = 0
END_EPOCH = 30
BATCH_SIZE = 128  # 如果显存不够，调小这个值 (例如 64 或 32)
LEARNING_RATE = 1e-4  # 微调通常使用较小的学习率
WEIGHT_DECAY = 1e-4
GRADIENT_CLIP = 1.0

# 模型路径
LOAD_FROM = "bioclip2_snake_epoch_best.pth"
SAVE_DIR = "./checkpoints"
LOG_FILE = "./training_log.txt"

# 数据增强
TRAIN_VAL_SPLIT = 0.9  # 如果找不到验证集CSV，使用90%训练，10%验证

# 早停设置
PATIENCE = 5
MIN_DELTA = 0.001

# 混合精度训练 (自动检测)
USE_AMP = torch.cuda.is_available()

# 随机种子
SEED = 42

# 根据平台设置 num_workers (WSL/Linux推荐4，Windows推荐0或2)
NUM_WORKERS = 4 if platform.system() != 'Windows' else 0


# ===========================================

def set_seed(seed=42):
    """设置随机种子以确保可复现性"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    print(f"✓ 随机种子设置为: {seed}")


class SnakeDataset(Dataset):
    """蛇类图像数据集"""

    def __init__(self, dataframe, root_dir, transform=None, species_to_idx=None):
        """
        Args:
            dataframe: pandas DataFrame 或 CSV 路径
            root_dir: 图片根目录
            transform: 图片预处理
            species_to_idx: 类别映射字典
        """
        if isinstance(dataframe, str):
            print(f"正在读取 CSV: {dataframe} ...")
            self.annotations = pd.read_csv(dataframe)
        else:
            self.annotations = dataframe

        self.root_dir = root_dir
        self.transform = transform

        # 建立或使用现有的类别映射
        if species_to_idx is None:
            self.species_list = sorted(self.annotations['binomial_name'].unique().tolist())
            self.species_to_idx = {name: idx for idx, name in enumerate(self.species_list)}
        else:
            self.species_to_idx = species_to_idx
            self.species_list = list(species_to_idx.keys())

            # 过滤掉不在训练集类别中的数据（针对验证集）
            initial_len = len(self.annotations)
            self.annotations = self.annotations[
                self.annotations['binomial_name'].isin(self.species_to_idx.keys())
            ].reset_index(drop=True)
            if len(self.annotations) < initial_len:
                print(f"过滤未知类别: {initial_len} -> {len(self.annotations)}")

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, index):
        # 简单的重试机制，如果图片损坏，尝试取下一张
        for i in range(3):  # 最多重试3次
            curr_idx = (index + i) % len(self.annotations)
            row = self.annotations.iloc[curr_idx]

            rel_path = row['image_path']
            img_path = os.path.join(self.root_dir, rel_path)
            species_name = row['binomial_name']
            label_idx = self.species_to_idx[species_name]

            try:
                image = Image.open(img_path).convert("RGB")
                if self.transform:
                    image = self.transform(image)
                return image, label_idx, img_path
            except Exception as e:
                print(f"警告: 图片加载失败 ({img_path}): {e}，尝试下一张...")

        # 如果3次都失败（极罕见），返回一个随机噪音图防止Crash
        print(f"严重错误: 无法加载索引 {index} 附近的图片")
        return torch.zeros((3, 224, 224)), label_idx, "broken_image"


class Trainer:
    def __init__(self, config):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"使用设备: {self.device}")

        os.makedirs(SAVE_DIR, exist_ok=True)

        # 1. 初始化模型
        self._init_model()

        # 2. 准备数据
        self._prepare_data()

        # 3. 初始化优化器
        self._init_optimizer()

        # 4. 混合精度
        self.scaler = torch.cuda.amp.GradScaler(enabled=USE_AMP)

        # 5. 状态变量
        self.start_epoch = START_EPOCH
        self.best_val_acc = 0.0
        self.best_val_loss = float('inf')
        self.patience_counter = 0

        # 6. 加载检查点
        if os.path.exists(LOAD_FROM):
            self._load_checkpoint()

        # 保存配置
        with open(os.path.join(SAVE_DIR, "config.json"), 'w') as f:
            json.dump(config, f, indent=4)

    def _init_model(self):
        print("正在加载 BioCLIP 2 ...")
        # 加载模型
        model, train_transform, val_transform = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
        self.model = model.to(self.device)
        self.train_transform = train_transform
        self.val_transform = val_transform

        # 冻结主干网络
        for param in self.model.parameters():
            param.requires_grad = False
        self.model.eval()

        # 动态获取特征维度
        with torch.no_grad():
            dummy = torch.zeros(1, 3, 224, 224).to(self.device)
            feat_dim = self.model.encode_image(dummy).shape[-1]
            print(f"模型特征维度: {feat_dim}")

        self.feature_dim = feat_dim

    def _prepare_data(self):
        print("准备数据...")

        # 读取训练CSV建立类别索引
        train_df = pd.read_csv(TRAIN_CSV)

        # 初始化分类头
        species_list = sorted(train_df['binomial_name'].unique().tolist())
        self.num_classes = len(species_list)
        self.species_to_idx = {name: idx for idx, name in enumerate(species_list)}
        print(f"类别数量: {self.num_classes}")

        self.classification_head = nn.Linear(self.feature_dim, self.num_classes).to(self.device)

        # 构建数据集
        # 检查是否有独立的验证集CSV
        if os.path.exists(VAL_CSV):
            print(f"发现验证集 CSV: {VAL_CSV}")
            self.train_dataset = SnakeDataset(train_df, DATA_PATH, self.train_transform, self.species_to_idx)
            self.val_dataset = SnakeDataset(VAL_CSV, DATA_PATH, self.val_transform, self.species_to_idx)
        else:
            print("未找到验证集 CSV，从训练集分割...")
            full_dataset = SnakeDataset(train_df, DATA_PATH, None, self.species_to_idx)  # 先不加transform

            train_size = int(TRAIN_VAL_SPLIT * len(full_dataset))
            val_size = len(full_dataset) - train_size

            train_subset, val_subset = random_split(
                full_dataset, [train_size, val_size],
                generator=torch.Generator().manual_seed(SEED)
            )

            # 使用包装类分别应用 transform
            class SubsetWrapper(Dataset):
                def __init__(self, subset, transform):
                    self.subset = subset
                    self.transform = transform

                def __len__(self): return len(self.subset)

                def __getitem__(self, idx):
                    img, label, path = self.subset[idx]
                    if self.transform: img = self.transform(img)
                    return img, label, path

            self.train_dataset = SubsetWrapper(train_subset, self.train_transform)
            self.val_dataset = SubsetWrapper(val_subset, self.val_transform)

        # DataLoader
        self.train_loader = DataLoader(
            self.train_dataset, batch_size=BATCH_SIZE, shuffle=True,
            num_workers=NUM_WORKERS, pin_memory=True, persistent_workers=(NUM_WORKERS > 0)
        )
        self.val_loader = DataLoader(
            self.val_dataset, batch_size=BATCH_SIZE, shuffle=False,
            num_workers=NUM_WORKERS, pin_memory=True, persistent_workers=(NUM_WORKERS > 0)
        )
        print(f"训练集: {len(self.train_dataset)}, 验证集: {len(self.val_dataset)}")

    def _init_optimizer(self):
        self.optimizer = optim.AdamW(
            self.classification_head.parameters(),
            lr=LEARNING_RATE,
            weight_decay=WEIGHT_DECAY
        )
        self.scheduler = CosineAnnealingLR(
            self.optimizer, T_max=END_EPOCH, eta_min=1e-6
        )
        self.criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    def _load_checkpoint(self):
        try:
            print(f"正在加载检查点: {LOAD_FROM}")
            checkpoint = torch.load(LOAD_FROM, map_location=self.device)

            if 'classification_head' in checkpoint:
                self.classification_head.load_state_dict(checkpoint['classification_head'])
                self.optimizer.load_state_dict(checkpoint['optimizer'])
                self.scheduler.load_state_dict(checkpoint['scheduler'])
                self.start_epoch = checkpoint['epoch'] + 1  # 关键：恢复epoch
                self.best_val_acc = checkpoint.get('best_val_acc', 0.0)
                print(f"✓ 恢复训练: Epoch {self.start_epoch}, 最佳 Acc: {self.best_val_acc:.2f}%")
            else:
                self.classification_head.load_state_dict(checkpoint)
                print("✓ 仅加载了模型权重")
        except Exception as e:
            print(f"⚠️ 加载检查点失败: {e}，将从头开始训练")

    def _save_checkpoint(self, epoch, val_acc, val_loss, is_best=False):
        state = {
            'epoch': epoch,
            'classification_head': self.classification_head.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'scheduler': self.scheduler.state_dict(),
            'best_val_acc': self.best_val_acc,
            'species_to_idx': self.species_to_idx
        }
        torch.save(state, os.path.join(SAVE_DIR, "last_checkpoint.pth"))
        if is_best:
            torch.save(state, os.path.join(SAVE_DIR, "bioclip2_snake_epoch_best.pth"))
            print(f"✅ 保存最佳模型 (Acc: {val_acc:.2f}%)")

    def train_epoch(self, epoch):
        self.classification_head.train()
        total_loss, correct, total = 0, 0, 0

        pbar = tqdm(self.train_loader, desc=f"Epoch {epoch + 1}/{END_EPOCH} [Train]")
        for images, labels, _ in pbar:
            images, labels = images.to(self.device), labels.to(self.device)

            self.optimizer.zero_grad()

            with torch.cuda.amp.autocast(enabled=USE_AMP):
                with torch.no_grad():
                    features = self.model.encode_image(images)
                    features /= features.norm(dim=-1, keepdim=True)
                outputs = self.classification_head(features.float())
                loss = self.criterion(outputs, labels)

            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.classification_head.parameters(), GRADIENT_CLIP)
            self.scaler.step(self.optimizer)
            self.scaler.update()

            total_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

            pbar.set_postfix({'Loss': f"{total_loss / (pbar.n + 1):.4f}", 'Acc': f"{100 * correct / total:.2f}%"})

        return total_loss / len(self.train_loader), 100 * correct / total

    @torch.no_grad()
    def validate(self):
        self.classification_head.eval()
        total_loss, correct, total = 0, 0, 0

        pbar = tqdm(self.val_loader, desc="[Val]")
        for images, labels, _ in pbar:
            images, labels = images.to(self.device), labels.to(self.device)

            with torch.cuda.amp.autocast(enabled=USE_AMP):
                features = self.model.encode_image(images)
                features /= features.norm(dim=-1, keepdim=True)
                outputs = self.classification_head(features.float())
                loss = self.criterion(outputs, labels)

            total_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

            pbar.set_postfix({'Loss': f"{total_loss / (pbar.n + 1):.4f}", 'Acc': f"{100 * correct / total:.2f}%"})

        return total_loss / len(self.val_loader), 100 * correct / total

    def train(self):
        print(f"\n开始训练 (Epoch {self.start_epoch + 1} -> {END_EPOCH})")

        for epoch in range(self.start_epoch, END_EPOCH):
            train_loss, train_acc = self.train_epoch(epoch)
            val_loss, val_acc = self.validate()
            self.scheduler.step()

            # 日志
            log_msg = (f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                       f"Epoch {epoch + 1}: Train Loss {train_loss:.4f}, Acc {train_acc:.2f}% | "
                       f"Val Loss {val_loss:.4f}, Acc {val_acc:.2f}% | LR {self.optimizer.param_groups[0]['lr']:.2e}")
            print(log_msg)
            with open(LOG_FILE, 'a') as f:
                f.write(log_msg + "\n")

            # 保存最佳
            is_best = val_acc > self.best_val_acc + MIN_DELTA
            if is_best:
                self.best_val_acc = val_acc
                self.best_val_loss = val_loss
                self.patience_counter = 0
            else:
                self.patience_counter += 1

            self._save_checkpoint(epoch, val_acc, val_loss, is_best)

            if self.patience_counter >= PATIENCE:
                print(f"⚠️ 早停触发 (Epoch {epoch + 1})")
                break


def main():
    set_seed(SEED)
    config = {
        'data_path': DATA_PATH, 'train_csv': TRAIN_CSV, 'val_csv': VAL_CSV,
        'batch_size': BATCH_SIZE, 'lr': LEARNING_RATE
    }
    trainer = Trainer(config)
    trainer.train()


if __name__ == "__main__":
    main()
