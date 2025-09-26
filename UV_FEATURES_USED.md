# UV 功能使用總結

這份文檔記錄了在 DC_partybot 專案優化過程中使用的所有 uv 功能。

## 🚀 基本專案管理

### `uv init`
**用途：** 初始化一個新的 uv 專案
```bash
uv init
```
**效果：**
- 創建 `pyproject.toml` 配置檔案
- 設置基本的專案結構
- 創建 `.python-version` 檔案
- 自動設置 Python 版本需求

**在本專案中的結果：**
- 初始化了名為 `dc-partybot` 的專案
- 設置了 Python 3.11 版本需求
- 創建了基礎的 `pyproject.toml` 結構

---

## 📦 依賴項目管理

### `uv add`
**用途：** 添加依賴項目到專案中

#### 添加生產依賴項目
```bash
uv add discord.py python-dotenv aiohttp
uv add yt-dlp mutagen
uv add google-api-python-client google-auth google-auth-httplib2
uv add spotipy redis pynacl pycryptodomex
```

#### 添加開發依賴項目
```bash
uv add --dev black flake8 pytest pytest-asyncio mypy
```

**效果：**
- 自動解析並安裝依賴項目
- 更新 `pyproject.toml` 中的依賴列表
- 自動更新 `uv.lock` 鎖定檔案
- 處理依賴衝突和版本相容性

**在本專案中添加的套件：**

**生產依賴：**
- `discord.py` - Discord API 客戶端
- `python-dotenv` - 環境變數管理
- `aiohttp` - 非同步 HTTP 客戶端
- `yt-dlp` - YouTube 下載器
- `mutagen` - 音訊元數據處理
- `google-api-python-client` - Google API 客戶端
- `google-auth` - Google 認證
- `google-auth-httplib2` - Google HTTP 認證
- `spotipy` - Spotify API 客戶端
- `redis` - Redis 客戶端
- `pynacl` - 加密庫
- `pycryptodomex` - 加密工具

**開發依賴：**
- `black` - 代碼格式化工具
- `flake8` - 代碼檢查工具
- `mypy` - 類型檢查工具
- `pytest` - 測試框架
- `pytest-asyncio` - 非同步測試支援

---

## 🔄 專案同步與管理

### `uv sync`
**用途：** 同步專案依賴項目，確保環境與配置一致

```bash
uv sync
```

**效果：**
- 根據 `pyproject.toml` 安裝所有依賴項目
- 創建或更新虛擬環境
- 鎖定依賴版本到 `uv.lock`
- 確保開發環境的一致性

**使用場景：**
- 初次設置專案環境
- 其他開發者克隆專案後的環境設置
- 依賴項目更新後的環境同步

---

## 🏃‍♂️ 程式執行

### `uv run`
**用途：** 在專案虛擬環境中執行命令

#### 執行 Python 腳本
```bash
uv run python main.py
```

#### 執行開發工具
```bash
uv run black .          # 代碼格式化
uv run flake8 .         # 代碼檢查
uv run mypy .           # 類型檢查
uv run pytest          # 執行測試
```

**優勢：**
- 自動使用正確的 Python 環境
- 無需手動啟動虛擬環境
- 確保依賴項目的可用性

---

## 📊 專案資訊查看

### `uv tree`
**用途：** 顯示依賴關係樹

```bash
uv tree
```

**效果：**
- 以樹狀結構顯示所有依賴項目
- 顯示依賴的依賴關係
- 幫助理解專案的依賴結構
- 識別重複或衝突的依賴

**在本專案中的輸出示例：**
```
dc-partybot v0.1.0
├── aiohttp v3.12.15
│   ├── aiohappyeyeballs v2.6.1
│   ├── aiosignal v1.4.0
│   └── ...
├── discord-py v2.6.3
└── ...
```

---

## 🔧 高級配置功能

### 依賴群組 (Dependency Groups)
**配置位置：** `pyproject.toml`
```toml
[dependency-groups]
dev = [
    "black>=25.9.0",
    "flake8>=7.3.0",
    "mypy>=1.18.2",
    "pytest>=8.4.2",
    "pytest-asyncio>=1.2.0",
]
```

**用途：**
- 分離生產和開發依賴
- 支援條件安裝
- 更好的依賴管理

### 專案腳本配置
**配置位置：** `pyproject.toml`
```toml
[project.scripts]
bot = "main:main"
```

**效果：**
- 創建命令行入口點
- 簡化專案執行

---

## 📁 專案結構管理

### Build 系統配置
**配置位置：** `pyproject.toml`
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["."]
exclude = [
    "*.log",
    "logs/",
    "temp_audio/",
    "*.cookies",
    ".env*",
    "requirements.txt",
    "docker-compose.yml",
    "Dockerfile*",
]
```

**用途：**
- 配置專案建置方式
- 控制哪些檔案被包含在發佈版本中
- 排除敏感或不必要的檔案

---

## 🛠️ 開發工具整合

### 工具配置
uv 自動識別並使用 `pyproject.toml` 中的工具配置：

#### Black 配置
```toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
exclude = '''
/(
    \.eggs
  | \.git
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''
```

#### MyPy 配置
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
# ... 更多配置
```

#### Pytest 配置
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
```

---

## 🚦 效能與優勢

### 速度提升
- **安裝速度：** 比 pip 快 10-100 倍
- **依賴解析：** 更快的衝突檢測和解決
- **快取機制：** 智慧的套件快取

### 可靠性
- **依賴鎖定：** `uv.lock` 確保環境一致性
- **衝突檢測：** 自動檢測並解決依賴衝突
- **版本管理：** 精確的版本控制

### 開發體驗
- **統一介面：** 單一命令處理所有套件操作
- **自動環境：** 自動管理虛擬環境
- **現代標準：** 遵循 Python 社群最新標準

---

## 📝 最佳實踐

### 1. 專案初始化
```bash
uv init                    # 初始化專案
uv add <dependencies>      # 添加依賴
uv add --dev <dev-deps>    # 添加開發依賴
```

### 2. 日常開發
```bash
uv sync                    # 同步環境
uv run <command>           # 執行命令
uv add <new-package>       # 添加新套件
```

### 3. 專案分享
- 提交 `pyproject.toml` 和 `uv.lock`
- 其他開發者只需執行 `uv sync`
- 確保環境完全一致

---

## 🔗 相關檔案

在本專案中，uv 功能涉及的主要檔案：

- **`pyproject.toml`** - 專案配置和依賴定義
- **`uv.lock`** - 依賴鎖定檔案
- **`.python-version`** - Python 版本指定
- **`scripts.ps1`** - 便利腳本（整合 uv 命令）
- **`README.md`** - 更新了安裝和使用說明

這些 uv 功能讓 DC_partybot 專案擁有了現代 Python 開發的所有優勢，包括更快的安裝、更好的依賴管理和更簡潔的開發工作流程。