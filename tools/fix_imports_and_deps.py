#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一的模块路径修复工具
Universal Module Path Fix Tool

为所有示例文件添加正确的模块导入路径
"""

import os
import sys
from pathlib import Path
import re

def add_path_fix_to_file(file_path):
    """为Python文件添加路径修复代码"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有路径修复代码
        if 'sys.path.insert(0' in content and 'backtrader' in content:
            print(f"  ⚠️  {file_path} 已有路径修复代码")
            return False
        
        # 在导入语句之前添加路径修复代码
        path_fix_code = '''import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

'''
        
        # 找到第一个import语句的位置
        import_pattern = r'^(import\s+|from\s+\w+\s+import)'
        match = re.search(import_pattern, content, re.MULTILINE)
        
        if match:
            insert_pos = match.start()
            new_content = content[:insert_pos] + path_fix_code + content[insert_pos:]
        else:
            # 如果没找到import语句，在文件开头添加
            new_content = path_fix_code + content
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✅ 已修复: {file_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ 修复失败 {file_path}: {e}")
        return False

def fix_all_examples():
    """修复所有示例文件的导入路径"""
    print("🔧 开始统一修复模块导入路径")
    print("=" * 50)
    
    # 需要修复的示例目录
    example_dirs = [
        'examples',
        'samples/risk-management',
        'samples/monitoring-alerting', 
        'samples/configuration-management'
    ]
    
    fixed_count = 0
    error_count = 0
    
    for dir_path in example_dirs:
        if not os.path.exists(dir_path):
            continue
            
        print(f"\n📁 处理目录: {dir_path}")
        
        # 遍历目录中的所有.py文件
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    if add_path_fix_to_file(file_path):
                        fixed_count += 1
                    else:
                        error_count += 1
    
    print(f"\n📊 修复完成:")
    print(f"  ✅ 成功修复: {fixed_count} 个文件")
    print(f"  ❌ 处理失败: {error_count} 个文件")

def create_requirements_file():
    """创建requirements.txt文件"""
    requirements = [
        "backtrader>=1.9.76.123",
        "apscheduler>=3.10.0",
        "loguru>=0.7.0",
        "psutil>=5.9.0",
        "requests>=2.28.0",
        "yfinance>=0.2.0",
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "flask>=2.2.0",
        "flask-socketio>=5.3.0",
        "plotly>=5.11.0",
        "cryptography>=39.0.0",
        "pyyaml>=6.0",
        "influxdb-client>=1.36.0",
        "pymongo>=4.3.0",
        "redis>=4.4.0",
        "pika>=1.3.0",
        "kafka-python>=2.0.0",
        "minio>=7.1.0",
        "boto3>=1.26.0",
        "psycopg2-binary>=2.9.0",
        "pymysql>=1.0.0",
        "memcache>=0.0.1"
    ]
    
    with open('requirements.txt', 'w') as f:
        f.write("# Backtrader 企业版依赖包\n")
        f.write("# Enterprise Backtrader Dependencies\n\n")
        for req in requirements:
            f.write(f"{req}\n")
    
    print("✅ 已创建 requirements.txt 文件")

def install_missing_dependencies():
    """安装缺失的依赖包"""
    print("\n📦 安装缺失的依赖包")
    print("=" * 30)
    
    required_packages = [
        'apscheduler',
        'loguru', 
        'psutil',
        'yfinance',
        'flask',
        'flask-socketio',
        'plotly',
        'cryptography',
        'pyyaml'
    ]
    
    installed_count = 0
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package} 已安装")
        except ImportError:
            print(f"  ⏬ 安装 {package}...")
            os.system(f"pip install {package}")
            installed_count += 1
    
    print(f"\n📊 依赖安装完成: 新安装 {installed_count} 个包")

if __name__ == "__main__":
    # 修复导入路径
    fix_all_examples()
    
    # 创建依赖文件
    create_requirements_file()
    
    # 安装缺失依赖
    install_missing_dependencies()
    
    print("\n🎉 所有修复和配置已完成！")