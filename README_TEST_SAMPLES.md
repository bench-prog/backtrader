# Backtrader Sample Test Runner

自动测试 backtrader samples 目录下所有示例脚本的工具。

## 功能特点

- ✅ 自动发现所有示例脚本
- ✅ 并行测试（可配置超时时间）
- ✅ 详细的测试报告
- ✅ 支持模式匹配过滤
- ✅ 自动禁用绘图功能

## 使用方法

### 基本用法

```bash
# 测试所有示例
python test_samples.py

# 使用 btpy 环境测试
/Users/boalyh/miniconda3/envs/btpy/bin/python test_samples.py
```

### 高级选项

```bash
# 只测试特定模式的示例
python test_samples.py --pattern "data-*"

# 设置超时时间（秒）
python test_samples.py --timeout 60

# 显示详细输出
python test_samples.py --verbose

# 指定 Python 解释器
python test_samples.py --python /path/to/python

# 指定 samples 目录
python test_samples.py --samples-dir /path/to/samples
```

### 组合使用

```bash
# 测试所有 data 相关示例，超时 20 秒，显示详细输出
python test_samples.py --pattern "data" --timeout 20 --verbose
```

## 测试结果说明

- ✅ **PASSED**: 示例成功运行，退出码为 0
- ❌ **FAILED**: 示例运行失败，退出码非 0
- ⏱️ **TIMEOUT**: 示例运行超时
- ⚠️ **SKIPPED**: 示例被跳过（通常是因为依赖问题）

## 示例

### 测试 pandas 相关示例

```bash
python test_samples.py --pattern "pandas"
```

输出：
```
######################################################################
# Backtrader Sample Test Runner
# Found 2 sample files
# Python: /usr/bin/python3
# Timeout: 30s
######################################################################

[1/2] 
======================================================================
Testing: samples/data-pandas/data-pandas-optix.py
======================================================================
✅ PASSED (0.37s)

[2/2] 
======================================================================
Testing: samples/data-pandas/data-pandas.py
======================================================================
✅ PASSED (1.23s)

======================================================================
TEST SUMMARY
======================================================================
Total:   2
✅ Passed:  2 (100.0%)
❌ Failed:  0 (0.0%)
⏱️  Timeout: 0 (0.0%)
⚠️  Skipped: 0 (0.0%)
======================================================================
```

## 注意事项

1. **超时设置**: 某些示例可能需要较长时间运行，建议根据实际情况调整 `--timeout` 参数
2. **依赖检查**: 某些示例可能需要额外的依赖（如 talib），如果缺少依赖会被标记为 SKIPPED
3. **绘图功能**: 脚本会自动尝试禁用绘图功能（使用 `--noplot` 参数）

## 退出码

- `0`: 所有测试通过
- `1`: 有测试失败

## 常见问题

### Q: 为什么有些示例超时？
A: 某些示例可能需要下载数据或进行大量计算。可以使用 `--timeout` 增加超时时间。

### Q: 如何只测试特定目录下的示例？
A: 使用 `--pattern` 参数，例如 `--pattern "data-replay"`

### Q: 如何查看失败示例的详细错误？
A: 使用 `--verbose` 参数查看详细输出
