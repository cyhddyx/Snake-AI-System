import os
import torch
import pandas as pd
import open_clip
from torch import nn
from PIL import Image
import torch.nn.functional as F

# ================= 配置区域 =================
MODEL_PATH = "bioclip2_snake_best.pth"
CSV_PATH = "/mnt/e/Project/Snake-AI-System/SnakeCLEF2023-TrainMetadata-iNat.csv"

# CSV 中表示国家的列名，通常是 'country' 或 'code'
# 请打开你的 CSV 确认一下，如果是国家代码(CN, US)就填 'code'，如果是全称就填 'country'
COUNTRY_COLUMN = 'code'


# ===========================================

class SnakePredictor:
    def __init__(self, model_path, csv_path):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"正在初始化预测器 (设备: {self.device})...")

        # 1. 加载类别和地理分布知识库
        print("正在构建[蛇类-地理位置]知识库...")
        df = pd.read_csv(csv_path)

        # 确保国家列是字符串，并处理空值
        df[COUNTRY_COLUMN] = df[COUNTRY_COLUMN].fillna('Unknown').astype(str)

        # 获取类别列表
        self.species_list = sorted(df['binomial_name'].unique().tolist())
        self.num_classes = len(self.species_list)

        # === 核心：构建地理字典 ===
        # 格式: {'Naja naja': {'India', 'China', ...}, ...}
        self.species_locations = {}
        for species, group in df.groupby('binomial_name'):
            # 获取该蛇种出现过的所有国家，转为小写以便匹配
            countries = set(x.lower() for x in group[COUNTRY_COLUMN].unique())
            self.species_locations[species] = countries

        print(f"知识库构建完成！包含 {self.num_classes} 种蛇的分布信息。")

        # 2. 加载 BioCLIP 2
        print("正在加载 BioCLIP 2 ...")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
        self.model.to(self.device)
        self.model.eval()

        # 3. 加载分类头
        print(f"正在加载权重: {model_path}")
        self.classification_head = nn.Linear(768, self.num_classes).to(self.device)

        if os.path.exists(model_path):
            self.classification_head.load_state_dict(torch.load(model_path, map_location=self.device))
            self.classification_head.eval()
            print("✅ 模型加载成功！")
        else:
            raise FileNotFoundError(f"❌ 找不到权重: {model_path}")

    def predict(self, image_path, location=None, top_k=5):
        if not os.path.exists(image_path):
            return f"错误: 找不到图片 {image_path}"

        try:
            # 1. 图像推理
            image = Image.open(image_path).convert("RGB")

            # TTA (简单的翻转增强，提高准确率)
            inputs = [self.preprocess(image), self.preprocess(image.transpose(Image.FLIP_LEFT_RIGHT))]
            image_input = torch.stack(inputs).to(self.device)

            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                logits = self.classification_head(image_features.float())
                probs = F.softmax(logits, dim=1)
                avg_probs = torch.mean(probs, dim=0)  # 取平均

            # 2. === 地理位置过滤逻辑 ===
            final_probs = avg_probs.clone()

            if location and location.strip():
                user_loc = location.strip().lower()
                print(f"🌍 正在应用地理过滤器: 仅保留分布在 '{user_loc}' 的蛇类...")

                for idx, species_name in enumerate(self.species_list):
                    known_locations = self.species_locations.get(species_name, set())

                    # 如果这条蛇的已知分布里不包含用户输入的国家
                    # 注意：这里用简单的字符串包含匹配
                    is_found = False
                    for loc in known_locations:
                        if user_loc in loc or loc in user_loc:
                            is_found = True
                            break

                    if not is_found:
                        # 惩罚：将概率缩小 1000 倍 (几乎排除)
                        final_probs[idx] *= 0.001
                    else:
                        # 奖励：概率稍微放大 (可选)
                        final_probs[idx] *= 1.2

            # 3. 重新排序取 Top K
            top_probs, top_indices = torch.topk(final_probs, top_k)

            results = []
            for i in range(top_k):
                score = top_probs[i].item() * 100
                class_idx = top_indices[i].item()
                species_name = self.species_list[class_idx]

                # 获取该蛇的分布国家用于展示
                locs = list(self.species_locations.get(species_name, []))[:3]  # 只显示前3个
                loc_str = ",".join(locs)

                results.append((species_name, score, loc_str))

            return results

        except Exception as e:
            return f"预测出错: {str(e)}"


# ================= 主程序 =================
if __name__ == "__main__":
    predictor = SnakePredictor(MODEL_PATH, CSV_PATH)

    print("\n💡 提示：输入图片路径后，你可以选择输入拍摄国家（英文），这能极大提高准确率！")

    while True:
        print("\n" + "=" * 40)
        # 1. 输入图片
        raw_path = input("1. 请输入图片路径 (q 退出): ").strip()
        img_path = raw_path.replace('"', '').replace("'", "")

        # 智能路径修复
        if ":" in img_path or "\\" in img_path:
            img_path = img_path.replace("\\", "/")
            if ":" in img_path:
                drive, rest = img_path.split(":", 1)
                img_path = f"/mnt/{drive.lower()}{rest}"

        if raw_path.lower() == 'q': break
        if not img_path: continue

        # 2. 输入位置 (可选)
        location = input("2. 请输入拍摄国家 (例如 China, India, Brazil，不填则回车): ").strip()

        print(f"正在识别...")
        predictions = predictor.predict(img_path, location)

        if isinstance(predictions, list):
            print("\n🏆 最终识别结果:")
            print("-" * 50)
            print(f"{'蛇名':<30} | {'置信度':<8} | {'已知分布 (部分)'}")
            print("-" * 50)
            for i, (name, score, locs) in enumerate(predictions):
                print(f"{i + 1}. {name:<28} | {score:.2f}%   | {locs}...")
        else:
            print(predictions)
