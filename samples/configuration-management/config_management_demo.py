#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级配置管理完整示例
Enterprise Configuration Management Demonstration

展示如何使用新添加的配置管理功能：
1. 多环境配置管理
2. 密钥安全管理
3. 配置版本控制
4. 环境切换和部署
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import datetime
import sys
import os
import json
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def demonstrate_environment_management():
    """演示环境管理功能"""
    print("\n" + "="*60)
    print("🌍 环境管理演示")
    print("="*60)
    
    # 创建配置管理器
    config_mgr = bt.config.create_config_manager()
    
    # 查看可用环境
    available_envs = config_mgr.environment_manager.get_available_environments()
    print(f"📋 可用环境: {available_envs}")
    
    # 切换到不同环境
    environments = ['development', 'testing', 'staging', 'production']
    
    for env in environments:
        print(f"\n--- 切换到 {env.upper()} 环境 ---")
        
        try:
            # 使用环境切换器
            switcher = bt.config.EnvironmentSwitcher(config_mgr)
            switcher.switch_to_environment(env)
            
            # 查看当前环境配置
            current_env = config_mgr.environment_manager.get_environment()
            current_config = config_mgr.get_config()
            
            print(f"当前环境: {current_env}")
            print(f"最大杠杆: {current_config.get('risk', {}).get('max_leverage', 'N/A')}")
            print(f"最大仓位: {current_config.get('risk', {}).get('max_position_size', 'N/A')}")
            print(f"调试模式: {current_config.get('environment', {}).get('debug', 'N/A')}")
            
        except Exception as e:
            print(f"❌ 环境切换失败: {e}")


def demonstrate_secret_management():
    """演示密钥管理功能"""
    print("\n" + "="*60)
    print("🔐 密钥管理演示")
    print("="*60)
    
    # 创建配置管理器
    config_mgr = bt.config.create_config_manager()
    
    # 存储各种密钥
    secrets = [
        ('binance_api_key', 'sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', 'Binance API密钥'),
        ('binance_secret', 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', 'Binance API密钥'),
        ('database_password', 'secure_db_password_123', '数据库密码'),
        ('email_smtp_password', 'email_app_password', '邮箱SMTP密码'),
        ('webhook_secret', 'whsec_xxxxxxxxxxxxxxxx', 'Webhook密钥')
    ]
    
    print("🔒 存储密钥:")
    for key, value, description in secrets:
        config_mgr.set_secret(key, value, description)
        print(f"  ✓ {key}: {description}")
    
    # 查看密钥列表（不显示实际值）
    print(f"\n📋 密钥列表:")
    secret_list = config_mgr.list_secrets()
    for secret_info in secret_list:
        print(f"  🔑 {secret_info['key']} - {secret_info['description']}")
        print(f"     创建时间: {secret_info['created_at']}")
    
    # 检索密钥
    print(f"\n🔓 检索密钥测试:")
    try:
        api_key = config_mgr.get_secret('binance_api_key')
        print(f"  Binance API密钥: {api_key[:10]}...{api_key[-4:]}")
    except Exception as e:
        print(f"  ❌ 密钥检索失败: {e}")
    
    # 访问日志
    print(f"\n📝 访问日志 (最近5条):")
    access_log = config_mgr.secret_manager.get_access_log(limit=5)
    for log_entry in access_log:
        print(f"  {log_entry['timestamp']} - {log_entry['action']} - {log_entry['key']}")


def demonstrate_config_validation():
    """演示配置验证功能"""
    print("\n" + "="*60)
    print("✅ 配置验证演示")
    print("="*60)
    
    # 创建配置管理器
    config_mgr = bt.config.create_config_manager()
    
    # 测试有效配置
    print("🧪 测试有效配置:")
    valid_config = {
        'risk': {
            'max_leverage': 2.0,
            'max_position_size': 0.1,
            'max_daily_loss': 0.05
        },
        'database': {
            'host': 'localhost',
            'port': 5432,
            'database': 'backtrader'
        },
        'logging': {
            'enabled': True,
            'level': 'INFO'
        }
    }
    
    try:
        config_mgr.set_config(valid_config, "有效配置测试")
        print("  ✓ 有效配置通过验证")
    except Exception as e:
        print(f"  ❌ 有效配置验证失败: {e}")
    
    # 测试无效配置
    print("\n🧪 测试无效配置:")
    invalid_configs = [
        {
            'name': '负杠杆配置',
            'config': {
                'risk': {'max_leverage': -1.0}  # 负杠杆
            }
        },
        {
            'name': '端口超出范围',
            'config': {
                'database': {'port': 99999}  # 端口号超出范围
            }
        },
        {
            'name': '缺少必需字段',
            'config': {
                'risk': {}  # 缺少必需字段
            }
        }
    ]
    
    for test_case in invalid_configs:
        try:
            config_mgr.set_config(test_case['config'], test_case['name'])
            print(f"  ❌ {test_case['name']}: 应该失败但通过了")
        except Exception as e:
            print(f"  ✓ {test_case['name']}: 正确捕获错误 - {str(e)[:50]}...")


def demonstrate_version_control():
    """演示配置版本控制功能"""
    print("\n" + "="*60)
    print("🔄 配置版本控制演示")
    print("="*60)
    
    # 创建配置管理器
    config_mgr = bt.config.create_config_manager()
    
    # 创建多个版本的配置
    print("📝 创建配置版本:")
    
    # 版本1: 基础配置
    config_v1 = {
        'risk': {'max_leverage': 1.0, 'max_position_size': 0.05},
        'trading': {'symbols': ['BTC/USDT'], 'initial_capital': 10000}
    }
    config_mgr.set_config(config_v1, "基础配置版本")
    print("  ✓ 版本1: 基础配置")
    
    # 版本2: 增加杠杆
    config_v2 = config_mgr.get_config()
    config_v2['risk']['max_leverage'] = 2.0
    config_mgr.set_config(config_v2, "增加杠杆到2.0")
    print("  ✓ 版本2: 增加杠杆")
    
    # 版本3: 增加交易对
    config_v3 = config_mgr.get_config()
    config_v3['trading']['symbols'].append('ETH/USDT')
    config_mgr.set_config(config_v3, "增加ETH交易对")
    print("  ✓ 版本3: 增加ETH交易对")
    
    # 查看版本历史
    print(f"\n📋 版本历史:")
    versions = config_mgr.get_version_history()
    for i, version in enumerate(reversed(versions[-5:]), 1):  # 显示最近5个版本
        print(f"  V{i}: {version['hash'][:8]} - {version['description']}")
        print(f"     创建时间: {version['created_at']}")
    
    # 比较版本差异
    print(f"\n🔍 版本差异比较:")
    if len(versions) >= 2:
        latest_version = versions[-1]['hash']
        previous_version = versions[-2]['hash']
        
        diff = config_mgr.version_manager.compare_versions(previous_version, latest_version)
        
        if diff['modified']:
            print("  修改的配置:")
            for section, changes in diff['modified'].items():
                print(f"    {section}: {changes}")
        else:
            print("  无配置修改")
    
    # 回滚配置
    print(f"\n⏪ 配置回滚测试:")
    if len(versions) >= 3:
        rollback_version = versions[-3]['hash']
        print(f"  回滚到版本: {rollback_version[:8]}")
        
        try:
            config_mgr.rollback_config(rollback_version)
            current_config = config_mgr.get_config()
            print(f"  ✓ 回滚成功")
            print(f"    当前杠杆: {current_config['risk']['max_leverage']}")
            print(f"    交易对数量: {len(current_config['trading']['symbols'])}")
        except Exception as e:
            print(f"  ❌ 回滚失败: {e}")


def demonstrate_project_initialization():
    """演示项目初始化功能"""
    print("\n" + "="*60)
    print("🏗️  项目初始化演示")
    print("="*60)
    
    # 创建临时项目目录
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp(prefix='bt_config_demo_')
    print(f"📁 创建临时项目目录: {temp_dir}")
    
    try:
        # 初始化开发环境
        print("\n🔧 初始化开发环境:")
        config_mgr = bt.config.initialize_environment(
            env_name="development",
            project_path=temp_dir
        )
        
        # 查看生成的目录结构
        print(f"\n📂 生成的目录结构:")
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(temp_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
        
        # 查看生成的配置文件
        config_file = os.path.join(temp_dir, 'config', 'config.json')
        if os.path.exists(config_file):
            print(f"\n📄 生成的配置文件内容:")
            with open(config_file, 'r') as f:
                config_content = json.load(f)
                print(json.dumps(config_content, indent=2, ensure_ascii=False))
        
        # 查看环境变量文件
        env_file = os.path.join(temp_dir, '.env')
        if os.path.exists(env_file):
            print(f"\n📄 生成的环境变量文件:")
            with open(env_file, 'r') as f:
                print(f.read())
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n🗑️  清理临时目录: {temp_dir}")


def demonstrate_config_hot_reload():
    """演示配置热更新功能"""
    print("\n" + "="*60)
    print("⚡ 配置热更新演示")
    print("="*60)
    
    # 创建配置管理器
    config_mgr = bt.config.create_config_manager()
    
    # 添加配置变更监听器
    def config_change_listener(event_type, data):
        print(f"🔔 配置变更通知: {event_type}")
        if event_type == 'config_updated':
            print(f"   新版本: {data['version'][:8]}")
            print(f"   描述: {data['description']}")
        elif event_type == 'config_item_updated':
            print(f"   更新项: {data['section']}.{data['key']}")
            print(f"   新值: {data['value']}")
    
    config_mgr.add_watcher(config_change_listener)
    
    # 模拟配置更新
    print("🔄 模拟配置热更新:")
    
    updates = [
        ('risk', 'max_leverage', 3.0, '提高最大杠杆'),
        ('risk', 'max_position_size', 0.15, '调整最大仓位'),
        ('logging', 'level', 'DEBUG', '启用调试日志')
    ]
    
    for section, key, value, description in updates:
        print(f"\n更新 {section}.{key} = {value}")
        config_mgr.update_config(section, key, value, description)
        time.sleep(0.5)  # 模拟时间间隔
    
    print(f"\n✅ 配置热更新演示完成")


def demonstrate_security_features():
    """演示安全特性"""
    print("\n" + "="*60)
    print("🛡️  安全特性演示")
    print("="*60)
    
    # 创建配置管理器
    config_mgr = bt.config.create_config_manager()
    
    # 演示加密功能
    print("🔐 加密功能测试:")
    
    # 存储敏感信息
    sensitive_data = "这是非常敏感的信息，不应该明文存储"
    config_mgr.set_secret('sensitive_info', sensitive_data, '测试敏感信息')
    
    # 验证加密存储
    stored_secret = config_mgr.secret_manager.secrets['sensitive_info']
    print(f"  存储的密文: {stored_secret['value'][:20]}...")
    
    # 验证解密正确性
    retrieved_data = config_mgr.get_secret('sensitive_info')
    print(f"  解密验证: {retrieved_data == sensitive_data}")
    
    # 演示密码强度
    print(f"\n🔑 密码管理:")
    print(f"  主密码长度: {len(config_mgr.crypto_manager.master_password)} 字符")
    print(f"  加密密钥长度: {len(config_mgr.crypto_manager.key)} 字节")
    
    # 演示访问控制
    print(f"\n👮 访问控制:")
    access_log = config_mgr.secret_manager.get_access_log()
    print(f"  访问记录数量: {len(access_log)}")
    
    if access_log:
        last_access = access_log[-1]
        print(f"  最后访问: {last_access['timestamp']} - {last_access['action']} - {last_access['key']}")


def main():
    """主函数"""
    print("🏛️  Backtrader企业级配置管理系统演示")
    print("Enterprise Configuration Management System Demonstration")
    print("="*60)
    
    try:
        # 演示各个配置管理功能
        demonstrate_environment_management()
        demonstrate_secret_management()
        demonstrate_config_validation()
        demonstrate_version_control()
        demonstrate_project_initialization()
        demonstrate_config_hot_reload()
        demonstrate_security_features()
        
        print("\n" + "="*60)
        print("🎉 所有配置管理功能演示完成!")
        print("="*60)
        print("\n📋 新增配置管理功能总结:")
        print("  ✅ 多环境配置管理 - dev/test/staging/prod环境隔离")
        print("  ✅ 密钥安全管理 - 加密存储、访问控制、审计日志")
        print("  ✅ 配置版本控制 - 版本历史、差异比较、配置回滚")
        print("  ✅ 配置验证机制 - 输入验证、类型检查、范围限制")
        print("  ✅ 项目初始化工具 - 标准目录结构、环境模板")
        print("  ✅ 配置热更新 - 运行时配置变更、监听器机制")
        print("  ✅ 安全特性 - 加密传输、权限控制、操作审计")
        
        print("\n🚀 使用建议:")
        print("  1. 在生产环境中使用强密码保护密钥")
        print("  2. 定期备份配置版本和密钥")
        print("  3. 使用环境变量管理敏感配置")
        print("  4. 启用配置变更审计日志")
        print("  5. 建立配置变更审批流程")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()