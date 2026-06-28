# warvault

warvault 是面向 Warcraft III / Y3 地图工程的本地资源库工具，用来扫描、索引、预览和标注模型、音效、图片资源。

产品设计：[docs/design.md](docs/design.md)。

## 项目结构

```text
warvault/
├── src/              # Python 后端服务
├── frontend/         # React 工作台
├── docs/             # 设计文档
├── tests/            # 自动化测试
├── update.bat        # Windows：安装 Python 与前端依赖
├── update.sh         # POSIX：安装 Python 与前端依赖
├── test.bat          # Windows：运行测试
└── test.sh           # POSIX：运行测试
```

## 命令行参数

入口命令：`python src`

| 长参数 | 短参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| --port | -p | 端口 | | 0 | 监听端口；0 表示随机选择空闲端口 |
| --version | -V | | | | 显示版本号并退出 |

## 使用

复制 `config.yaml.example` 为 `config.yaml`，填写本地资源源目录后启动：

```bash
copy config.yaml.example config.yaml
python -m app_main --port 8765
cd frontend && npm run dev
```

开发时 Vite 会把 `/api` 请求转发到 `127.0.0.1:8765`。

## 构建

```bash
cd frontend && npm run build
python -m app_main
```

构建后的页面由 Python 服务托管。
