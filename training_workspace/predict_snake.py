import os
import torch
import pandas as pd
import open_clip
from torch import nn
from PIL import Image
import torch.nn.functional as F

# ================= 配置区域 =================
# 1. 训练好的模型权重路径
MODEL_PATH = "bioclip2_snake_best.pth"

# 2. 训练集的 CSV (我们需要它来获取 1784 种蛇的名字列表)
# 注意：必须和训练时用的 CSV 一模一样，否则名字会张冠李戴！
CSV_PATH = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-TrainMetadata-iNat.csv"

# 3. 你想测试的图片路径 (随便找一张蛇的图)
TEST_IMAGE = ""


# (如果没有具体路径，可以先留空，运行代码时会提示你输入)
# ===========================================

class SnakePredictor:
    def __init__(self, model_path, csv_path):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"正在初始化预测器 (设备: {self.device})...")

        # 1. 准备类别列表 (必须和训练时完全一致)
        print("正在加载类别映射...")
        df = pd.read_csv(csv_path)
        self.species_list = sorted(df['binomial_name'].unique().tolist())
        self.num_classes = len(self.species_list)
        print(f"模型支持 {self.num_classes} 种蛇类识别。")

        # 2. 加载 BioCLIP 2 模型
        print("正在加载 BioCLIP 2 主干网络...")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
        self.model.to(self.device)
        self.model.eval()

        # 3. 加载分类头并读取权重
        print(f"正在加载微调权重: {model_path}")
        self.classification_head = nn.Linear(768, self.num_classes).to(self.device)

        if os.path.exists(model_path):
            state_dict = torch.load(model_path, map_location=self.device)
            self.classification_head.load_state_dict(state_dict)
            self.classification_head.eval()
            print("✅ 模型加载成功！")
        else:
            raise FileNotFoundError(f"❌ 找不到权重文件: {model_path}")

    def predict(self, image_path, top_k=5):
        """
        输入图片路径，返回前 K 个预测结果
        """
        if not os.path.exists(image_path):
            return f"错误: 找不到图片 {image_path}"

        try:
            # 1. 预处理图片
            image = Image.open(image_path).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)

            # 2. 推理
            with torch.no_grad():
                # 提取特征
                image_features = self.model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)

                # 分类
                logits = self.classification_head(image_features.float())

                # 计算概率 (Softmax)
                probs = F.softmax(logits, dim=1)

                # 获取前 K 名
                top_probs, top_indices = torch.topk(probs, top_k)

            # 3. 格式化结果
            results = []
            for i in range(top_k):
                score = top_probs[0][i].item() * 100  # 转成百分比
                class_idx = top_indices[0][i].item()
                species_name = self.species_list[class_idx]
                results.append((species_name, score))

            return results

        except Exception as e:
            return f"预测出错: {str(e)}"


# ================= 主程序 =================
if __name__ == "__main__":
    # 1. 初始化预测器 (只运行一次)
    predictor = SnakePredictor(MODEL_PATH, CSV_PATH)

    while True:
        print("\n" + "=" * 30)
        # 2. 获取用户输入的图片路径
        img_path = input("请输入图片路径 (输入 q 退出): ").strip()

        # 去除可能存在的引号 (Windows 复制路径时常带引号)
        img_path = img_path.replace('"', '').replace("'", "")

        if img_path.lower() == 'q':
            break

        if not img_path:
            continue

        # 3. 开始预测
        print(f"正在识别: {os.path.basename(img_path)} ...")
        predictions = predictor.predict(img_path)

        if isinstance(predictions, list):
            print("\n🏆 识别结果 (Top 5):")
            print("-" * 30)
            for i, (name, score) in enumerate(predictions):
                # 打印漂亮的进度条
                bar_len = int(score / 2)
                bar = "█" * bar_len + "░" * (50 - bar_len)
                print(f"{i + 1}. {name:<30} | {score:.2f}%")
                print(f"   [{bar}]")
        else:
            print(predictions)
