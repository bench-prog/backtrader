#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Download Multiple Timeframe Data for Grid Trading Test
=====================================================

使用数据下载工具下载Binance BTC/USDT的多个时间周期数据，
用于网格交易策略的多周期测试。
"""

import os
import sys
import subprocess
import time
from datetime import datetime, timedelta

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def run_download_command(cmd_args):
    """运行下载命令"""
    try:
        # 直接调用Python脚本而不是模块
        script_path = os.path.join(project_root, "data_downloader", "cli", "main.py")
        full_cmd = [sys.executable, script_path] + cmd_args[3:]  # 跳过 -m data_downloader.cli.main
        
        result = subprocess.run(
            full_cmd, 
            cwd=project_root,
            capture_output=True, 
            text=True, 
            timeout=1800  # 30分钟超时
        )
        if result.returncode == 0:
            print(f"✅ 下载成功: {' '.join(cmd_args[-1:])}")
            return True
        else:
            print(f"❌ 下载失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ 下载超时: {' '.join(cmd_args[-1:])}")
        return False
    except Exception as e:
        print(f"💥 下载异常: {e}")
        return False

def download_multiple_timeframes():
    """下载多个时间周期的数据"""
    print("🚀 开始下载Binance BTC/USDT多周期数据")
    print("=" * 50)
    
    # 设置下载参数
    exchange = "binance"
    symbol = "BTC/USDT"
    from_date = "2023-01-01"
    to_date = "2024-01-01"  # 下载一年数据用于测试
    
    # 时间周期配置
    timeframes = {
        "30m": "30分钟",
        "1h": "1小时", 
        "4h": "4小时"
    }
    
    # 输出目录
    output_dir = os.path.join(project_root, "datas", "grid_test")
    os.makedirs(output_dir, exist_ok=True)
    
    successful_downloads = []
    
    for timeframe, desc in timeframes.items():
        print(f"\n📥 正在下载 {desc} 数据...")
        
        output_file = os.path.join(output_dir, f"binance-btc-{timeframe}-2023.txt")
        
        # 构建命令
        cmd = [
            sys.executable, "-m", "data_downloader.cli.main", "ccxt",
            "--exchange", exchange,
            "--symbol", symbol,
            "--fromdate", from_date,
            "--todate", to_date,
            "--timeframe", timeframe,
            "--outfile", output_file
        ]
        
        # 执行下载
        if run_download_command(cmd):
            successful_downloads.append((timeframe, desc, output_file))
            # 添加延迟避免API限制
            time.sleep(2)
        else:
            print(f"⚠️ {desc} 数据下载失败")
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 下载结果汇总:")
    print(f"✅ 成功下载: {len(successful_downloads)} 个周期")
    
    for timeframe, desc, filepath in successful_downloads:
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            # 估算数据行数（简单方法）
            with open(filepath, 'r') as f:
                lines = sum(1 for _ in f)
            print(f"   • {desc} ({timeframe}): {lines-1} 行数据, {file_size/1024:.1f}KB")
    
    return successful_downloads

def test_grid_strategy_with_multiple_timeframes(downloaded_files):
    """使用多周期数据测试网格策略"""
    print("\n🧪 开始多周期网格策略测试")
    print("=" * 50)
    
    # 导入必要的模块
    import backtrader as bt
    import pandas as pd
    
    # 简化版网格策略（用于快速测试）
    class QuickGridStrategy(bt.Strategy):
        params = (
            ('grid_levels', 6),
            ('grid_spacing', 0.02),
        )
        
        def __init__(self):
            self.grid_lines = []
            self.positions = {}
            
        def start(self):
            price = self.data.close[0]
            for i in range(-self.p.grid_levels//2, self.p.grid_levels//2 + 1):
                grid_price = price * (1 + self.p.grid_spacing) ** i
                self.grid_lines.append(grid_price)
            print(f"🎯 网格初始化完成，当前价格: ${price:.2f}")
        
        def next(self):
            current_price = self.data.close[0]
            
            for grid_price in self.grid_lines:
                grid_id = f"grid_{grid_price:.2f}"
                
                # 买入信号
                if (len(self.data.close) > 1 and 
                    self.data.close[-1] > grid_price >= current_price and
                    grid_id not in self.positions):
                    
                    cash = self.broker.get_cash()
                    size = (cash * 0.1) / grid_price
                    if size > 0:
                        self.buy(size=size, price=grid_price)
                        self.positions[grid_id] = {'price': grid_price, 'size': size}
                        print(f"📈 买入: ${grid_price:.2f} × {size:.4f}")
                
                # 卖出信号
                elif (grid_id in self.positions and 
                      current_price >= grid_price * 1.01):
                    
                    position = self.positions[grid_id]
                    self.sell(size=position['size'])
                    pnl = (current_price - position['price']) * position['size']
                    print(f"📉 卖出: ${position['price']:.2f} → ${current_price:.2f}, 收益${pnl:.2f}")
                    del self.positions[grid_id]
    
    # 测试每个数据文件
    results = []
    
    for timeframe, desc, filepath in downloaded_files:
        print(f"\n🔬 测试 {desc} 数据...")
        
        try:
            # 加载数据
            df = pd.read_csv(filepath)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            
            # 创建回测引擎
            cerebro = bt.Cerebro()
            cerebro.addstrategy(QuickGridStrategy)
            cerebro.adddata(bt.feeds.PandasData(dataname=df))
            cerebro.broker.setcash(10000.0)
            cerebro.broker.setcommission(commission=0.001)
            
            # 运行回测
            initial_value = cerebro.broker.get_value()
            cerebro.run()
            final_value = cerebro.broker.get_value()
            
            # 计算结果
            returns = (final_value - initial_value) / initial_value * 100
            
            results.append({
                'timeframe': timeframe,
                'description': desc,
                'initial': initial_value,
                'final': final_value,
                'returns': returns,
                'data_points': len(df)
            })
            
            print(f"💰 初始资金: ${initial_value:,.2f}")
            print(f"💰 最终资金: ${final_value:,.2f}")
            print(f"📈 收益率: {returns:.2f}%")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            results.append({
                'timeframe': timeframe,
                'description': desc,
                'error': str(e)
            })
    
    # 输出汇总结果
    print("\n" + "=" * 60)
    print("🏆 多周期测试结果汇总:")
    print("=" * 60)
    
    successful_results = [r for r in results if 'error' not in r]
    
    if successful_results:
        # 按收益率排序
        successful_results.sort(key=lambda x: x['returns'], reverse=True)
        
        for result in successful_results:
            print(f"{result['description']:8} | "
                  f"收益率: {result['returns']:6.2f}% | "
                  f"数据点: {result['data_points']:5d} | "
                  f"最终资金: ${result['final']:8.2f}")
        
        best_result = successful_results[0]
        print(f"\n🥇 最佳表现: {best_result['description']} "
              f"(收益率: {best_result['returns']:.2f}%)")
    else:
        print("❌ 所有测试都失败了")
    
    return results

def main():
    """主函数"""
    print("🤖 Binance多周期网格交易数据下载与测试")
    print("=" * 60)
    
    # 下载数据
    downloaded_files = download_multiple_timeframes()
    
    if not downloaded_files:
        print("❌ 没有成功下载任何数据，退出测试")
        return
    
    # 测试策略
    test_results = test_grid_strategy_with_multiple_timeframes(downloaded_files)
    
    print(f"\n🎉 测试完成！共测试 {len(test_results)} 个时间周期")

if __name__ == "__main__":
    main()