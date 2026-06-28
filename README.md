# warvault

Warvault 是一个 Python 命令行工具项目。

## 项目结构

```text
warvault/
├── src/              # CLI 入口
├── tests/            # 测试
├── update.bat        # Windows：创建 venv 并安装依赖
├── update.sh         # POSIX：创建 venv 并安装依赖
├── test.bat          # Windows：运行测试
└── test.sh           # POSIX：运行测试
```

## 命令行参数

`python src`

| 长参数 | 短参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| --version | -V | | | | 显示版本号并退出 |
