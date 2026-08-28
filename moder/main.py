import io
import json
import torch
import open_clip
from torch import nn
from PIL import Image
import torch.nn.functional as F
from fastapi import FastAPI, File, UploadFile, HTTPException
from contextlib import asynccontextmanager

# ================= 配置区域 =================
MODEL_PATH = "bioclip2_snake_best.pth"
CLASS_JSON_PATH = "snake_classes.json"  # 刚才你保存的那个文件


# ===========================================

class SnakePredictorAPI:
    def __init__(self, model_path, json_path):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 [BioCLIP] 初始化中 (Device: {self.device})...")

        # 1. 加载类别列表 (替代 CSV)
        try:
            print(f"📖 正在读取类别文件: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                self.species_list = json.load(f)

            self.num_classes = len(self.species_list)
            print(f"📚 类别加载成功！共 {self.num_classes} 种蛇。")

            # 简单检查一下顺序
            print(f"   - ID 0: {self.species_list[0]}")
            print(f"   - ID {self.num_classes - 1}: {self.species_list[-1]}")

        except Exception as e:
            print(f"❌ JSON 读取失败: {e}")
            raise e

        # 2. 加载 BioCLIP 2 主干
        print("🧠 加载 BioCLIP 2 主干...")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
        self.model.to(self.device)
        self.model.eval()

        # 3. 加载微调权重
        print(f"🔧 加载微调权重: {model_path}")
        # 注意：这里必须确保分类头的输出维度和 JSON 里的数量一致
        self.classification_head = nn.Linear(768, self.num_classes).to(self.device)

        if torch.cuda.is_available():
            state_dict = torch.load(model_path)
        else:
            state_dict = torch.load(model_path, map_location="cpu")

        self.classification_head.load_state_dict(state_dict)
        self.classification_head.eval()
        print("✅ BioCLIP 服务就绪！")

    def predict(self, image_bytes, top_k=20):
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # TTA (原图 + 翻转)
            inputs = [self.preprocess(image), self.preprocess(image.transpose(Image.FLIP_LEFT_RIGHT))]
            image_input = torch.stack(inputs).to(self.device)

            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                logits = self.classification_head(image_features.float())
                probs = F.softmax(logits, dim=1)
                avg_probs = torch.mean(probs, dim=0)

            # 获取 Top K
            top_probs, top_indices = torch.topk(avg_probs, top_k)

            candidates = []
            for i in range(top_k):
                score = top_probs[i].item() * 100
                class_idx = top_indices[i].item()
                species_name = self.species_list[class_idx]

                candidates.append({
                    "rank": i + 1,
                    "species": species_name,
                    "confidence": round(score, 2)
                })

            return candidates

        except Exception as e:
            print(f"推理错误: {e}")
            return []


# ================= FastAPI =================
predictor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    predictor = SnakePredictorAPI(MODEL_PATH, CLASS_JSON_PATH)
    yield
    print("🛑 服务关闭")


app = FastAPI(title="BioCLIP Vision Service", lifespan=lifespan)
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="BioCLIP Vision Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/predict_candidates")
async def get_candidates(file: UploadFile = File(...)):
    if not predictor:
        raise HTTPException(status_code=500, detail="Model not loaded")

    image_bytes = await file.read()
    candidates = predictor.predict(image_bytes, top_k=20)

    return {
        "status": "success",
        "candidates": candidates
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)