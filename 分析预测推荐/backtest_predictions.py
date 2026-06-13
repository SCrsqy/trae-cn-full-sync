#!/usr/bin/env python3
"""
回测预测脚本
生成所有历史期的预测（回测模式）
"""
import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backtest_predictions():
    """执行回测"""
    logger.info("开始执行回测...")
    
    try:
        from business_rules import PredictionGenerator, AccuracyCalculator
        from core_algorithm import generate_prediction, calculate_accuracy
        
        db_path = '/Users/rs/AI/分析预测推荐/lottery.db'
        
        # 创建预测生成器和准确率计算器
        generator = PredictionGenerator(db_path)
        calculator = AccuracyCalculator(db_path)
        
        # 获取所有历史期号
        conn = generator.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT issue_number FROM lottery_data_am ORDER BY issue_number ASC")
        issues = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        logger.info(f"发现 {len(issues)} 个历史期号")
        
        # 为每个历史期号生成预测（回测模式）
        results = []
        for issue in issues[:10]:  # 限制只回测前10期作为演示
            logger.info(f"处理期号: {issue}")
            
            # 生成预测
            prediction = generator.generate_prediction('AM', issue)
            
            # 获取实际开奖数据
            conn = generator.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT numbers, zodiacs FROM lottery_data_am WHERE issue_number = ?", (issue,))
            row = cursor.fetchone()
            
            if row:
                import json
                actual_numbers = json.loads(row[0])
                actual_zodiacs = json.loads(row[1])
                
                # 计算准确率
                accuracy = calculator.update_prediction_accuracy(issue, 'AM')
                
                results.append({
                    'issue_number': issue,
                    'prediction_generated': True,
                    'accuracy_calculated': accuracy,
                    'timestamp': datetime.now().isoformat()
                })
            
            conn.close()
        
        logger.info(f"回测完成，共处理 {len(results)} 期")
        
        # 统计回测结果
        success_count = sum(1 for r in results if r['accuracy_calculated'])
        print(f"\n回测结果统计:")
        print(f"  总期数: {len(results)}")
        print(f"  成功计算准确率: {success_count}")
        print(f"  成功率: {(success_count / len(results)) * 100:.2f}%")
        
        return {'status': 'success', 'results': results}
    
    except Exception as e:
        logger.error(f"回测失败: {e}")
        return {'status': 'failed', 'error': str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='回测预测')
    args = parser.parse_args()
    
    result = backtest_predictions()
    
    if result['status'] == 'success':
        print("✅ 回测完成")
    else:
        print(f"❌ 回测失败: {result.get('error')}")