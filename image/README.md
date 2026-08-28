# image 模块说明文档

## 1. 模块定位

`image` 是 Snake AI System 中的图片资源服务模块，主要负责把本地蛇类图片转换成浏览器、前端页面或其他服务可以访问的 HTTP URL。

在系统中，图片通常来自两个来源：

- `images/`：项目内置的蛇类图片数据集
- `storage/`：用户上传或导入后保存的图片

本模块通过一个轻量级 HTTP 服务统一管理这些图片，让其他模块不需要直接读取本地磁盘路径，只需要通过 URL 获取图片。

## 2. 解决的问题

在前后端分离或浏览器环境中，前端不能直接访问服务器上的本地文件路径，例如：

```text
E:\Project\Snake-AI-System\image\images\Boa_constrictor\254274333.jpeg
```

因此需要一个图片 URL 服务，把本地图片映射成可访问地址，例如：

```text
http://127.0.0.1:8003/images/Boa_constrictor/254274333.jpeg
```

这样前端展示、模型识别结果展示、图片预览和接口联调都会更方便。

## 3. 目录结构

```text
image/
├── server.py          # 图片 URL 后端服务
├── README.md          # 模块说明文档
├── images/            # 原始蛇类图片数据集
├── storage/           # 上传或导入后的图片存储目录
└── test-sample.png    # 测试图片
```

当前 `images/` 目录中包含约 606 个蛇类类别目录、2439 张图片，可作为系统演示和模型测试的数据来源。

## 4. 核心功能

### 4.1 原始图片访问

`images/` 目录中的图片可以直接通过 URL 访问。

示例：

```text
images/Boa_constrictor/254274333.jpeg
```

对应 URL：

```text
http://127.0.0.1:8003/images/Boa_constrictor/254274333.jpeg
```

这个能力适合用于展示系统内置数据集，或者给识别模块提供测试图片。

### 4.2 本地图片导入

通过 `POST /api/images/import` 可以把任意本地图片复制到 `storage/` 目录，并返回一个可访问 URL。

这适合演示“用户选择本地图片后，系统生成图片地址并进行后续识别”的流程。

### 4.3 文件上传

通过 `POST /api/images/upload` 可以接收 multipart 文件上传，并保存到 `storage/` 目录。

这适合和前端上传组件对接，实现用户从浏览器上传图片。

### 4.4 图片列表查询

通过 `GET /api/source-images/list` 可以一次性获取 `images/` 目录下所有原始图片的 URL 列表。

这适合前端做图片库展示、随机测试图片选择、批量演示数据加载等功能。

## 5. 接口说明

### 5.1 健康检查

```http
GET /api/health
```

返回示例：

```json
{
  "status": "ok"
}
```

用途：确认图片服务是否正常启动。

### 5.2 导入本地图片

```http
POST /api/images/import
Content-Type: application/json
```

请求体：

```json
{
  "path": "E:\\Project\\Snake-AI-System\\image\\test-sample.png"
}
```

返回示例：

```json
{
  "filename": "ff3f0ca4ede143d2ad193f62f5cbfd14.png",
  "stored_path": "E:\\Project\\Snake-AI-System\\image\\storage\\ff3f0ca4ede143d2ad193f62f5cbfd14.png",
  "url": "http://127.0.0.1:8003/images/ff3f0ca4ede143d2ad193f62f5cbfd14.png"
}
```

处理流程：

```text
接收本地路径 -> 校验文件是否存在 -> 校验图片格式 -> 生成 UUID 文件名 -> 复制到 storage/ -> 返回访问 URL
```

### 5.3 上传图片文件

```http
POST /api/images/upload
Content-Type: multipart/form-data
```

字段说明：

```text
file: 要上传的图片文件
```

返回内容和导入接口一致，都会返回 `filename`、`stored_path` 和 `url`。

### 5.4 访问图片

```http
GET /images/<filename-or-relative-path>
```

示例：

```text
http://127.0.0.1:8003/images/ff3f0ca4ede143d2ad193f62f5cbfd14.png
http://127.0.0.1:8003/images/Boa_constrictor/254274333.jpeg
```

说明：

- 如果路径对应 `storage/` 中的文件，优先返回上传或导入后的图片
- 如果路径对应 `images/` 中的文件，则返回原始数据集图片
- 如果文件不存在，会返回 JSON 错误信息

### 5.5 访问原始图片

```http
GET /source-images/<relative-path>
```

示例：

```text
http://127.0.0.1:8003/source-images/Boa_constrictor/254274333.jpeg
```

该接口只访问 `images/` 目录，适合明确区分“数据集原图”和“用户上传图片”的场景。

### 5.6 获取原始图片列表

```http
GET /api/source-images/list
```

返回示例：

```json
{
  "count": 2439,
  "directory": "E:\\Project\\Snake-AI-System\\image\\images",
  "items": [
    {
      "relative_path": "Boa_constrictor/254274333.jpeg",
      "url": "http://127.0.0.1:8003/images/Boa_constrictor/254274333.jpeg"
    }
  ]
}
```

## 6. 启动方式

进入 `image` 目录：

```powershell
cd E:\Project\Snake-AI-System\image
```

启动服务：

```powershell
python server.py
```

默认监听：

```text
host: 0.0.0.0
port: 8003
```

启动成功后会输出：

```text
Image URL server started at http://0.0.0.0:8003
Storage directory: E:\Project\Snake-AI-System\image\storage
Source directory: E:\Project\Snake-AI-System\image\images
```

也可以指定监听地址和端口：

```powershell
python server.py --host 127.0.0.1 --port 9000
```

## 7. 调用示例

### 7.1 检查服务状态

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8003/api/health"
```

### 7.2 导入本地图片

```powershell
$body = @{
  path = "E:\Project\Snake-AI-System\image\test-sample.png"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8003/api/images/import" `
  -ContentType "application/json" `
  -Body $body
```

### 7.3 获取图片列表

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8003/api/source-images/list"
```

## 8. 关键实现说明

### 8.1 仅使用 Python 标准库

服务基于以下标准库实现：

- `http.server`：创建 HTTP 服务
- `pathlib`：处理跨平台文件路径
- `uuid`：生成唯一文件名，避免文件重名
- `mimetypes`：根据扩展名返回正确的图片 Content-Type
- `shutil`：复制本地图片
- `json`：处理接口请求和响应

因此本模块不需要额外安装 Flask、FastAPI 等第三方依赖，启动成本低，适合本地演示和答辩部署。

### 8.2 路径安全控制

代码中通过 `resolve_file_under()` 限制文件只能在指定目录下访问：

```text
storage/ 目录用于访问上传和导入后的图片
images/ 目录用于访问系统内置图片
```

这样可以避免通过 `../` 访问项目外部文件，提升基本安全性。

### 8.3 图片格式校验

当前允许的图片格式包括：

```text
.jpg, .jpeg, .png, .gif, .bmp, .webp, .svg
```

如果上传或导入的文件不是这些格式，接口会返回错误，避免把非图片文件放入图片存储目录。

### 8.4 跨域支持

服务在响应头中加入了 CORS 配置：

```text
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

这样前端项目即使运行在其他端口，也可以直接请求本图片服务。

## 9. 答辩讲解思路

答辩时可以按下面顺序介绍：

1. 先说明问题：浏览器不能直接访问后端本地文件路径，所以需要图片 URL 服务。
2. 再说明模块作用：`image` 模块把本地图片、上传图片和数据集图片统一转换成 HTTP URL。
3. 展示目录结构：`images/` 存放原始数据集，`storage/` 存放上传或导入图片，`server.py` 提供接口。
4. 演示启动服务：运行 `python server.py`，访问 `/api/health`。
5. 演示图片访问：打开 `/images/<图片路径>`，证明本地图片已经可通过浏览器访问。
6. 演示图片列表：调用 `/api/source-images/list`，说明前端可以批量获取数据集图片。
7. 说明安全设计：限制访问目录、校验图片格式、使用 UUID 防止文件名冲突。
8. 说明扩展方向：后续可接入数据库、对象存储、图片压缩、缩略图生成、权限控制等能力。

## 10. 模块优势

- 结构简单：一个 `server.py` 即可启动服务
- 依赖少：只依赖 Python 标准库
- 易演示：启动后可直接在浏览器访问图片 URL
- 易对接：接口返回 JSON，前端和识别模块都能方便使用
- 有基本安全控制：限制目录访问并校验图片格式
- 可扩展：后续可以替换为对象存储或接入更完整的后端框架

## 11. 后续可扩展方向

如果系统继续完善，本模块可以扩展以下能力：

- 图片元数据入库，例如图片名称、类别、上传时间、识别结果
- 图片缩略图生成，提升前端列表加载速度
- 图片压缩和尺寸标准化，减少存储占用
- 接入 MinIO、阿里云 OSS、AWS S3 等对象存储
- 增加用户权限控制，限制图片上传和访问范围
- 增加批量上传和批量删除接口
- 与蛇类识别模型联动，上传后自动触发识别流程

## 12. 一句话总结

`image` 模块是系统中的图片资源支撑层，它把本地蛇类图片数据集和用户上传图片统一转换成可访问 URL，为前端展示、模型测试和系统联调提供了基础能力。
