#!/usr/bin/env python3
"""
批量修复示例文件的导入问题
"""

import os
import re


def fix_import_issues():
    """修复导入问题"""

    # 需要修复的文件列表
    files_to_fix = [
        "real_trade/examples/dynamic_stop_loss_demo.py",
        "real_trade/examples/event_driven_trading_demo.py",
        "real_trade/examples/multi_factor_quant_demo.py",
        "real_trade/examples/smart_position_demo.py",
    ]

    # 通用修复模板
    import_fix_template = """import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
"""

    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            continue

        print(f"处理文件: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否已经有修复过的导入
            if "添加项目路径" in content:
                print("  已经修复过，跳过")
                continue

            # 查找相对导入模式
            relative_import_pattern = r"from \.\.[^\n]*import[^\n]*\n(?:[^\n]*\n)*?\)"

            # 替换相对导入为绝对导入
            if "from ..utils import" in content:
                # 添加路径设置
                content = re.sub(
                    r"(import .*\n\n)", r"\1" + import_fix_template, content, count=1
                )

                # 替换相对导入为绝对导入
                content = content.replace(
                    "from ..utils import", "from real_trade.utils import"
                )

                # 写回文件
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                print("  ✓ 修复完成")
            else:
                print("  未找到相对导入，跳过")

        except Exception as e:
            print(f"  ✗ 处理失败: {e}")


if __name__ == "__main__":
    fix_import_issues()
