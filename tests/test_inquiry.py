#!/usr/bin/env python3
"""
单元测试
测试核心功能
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestReportGenerator(unittest.TestCase):
    """测试报告生成器"""
    
    def test_report_generation(self):
        """测试报告生成"""
        from src.report_generator import ReportGenerator
        
        gen = ReportGenerator()
        
        products = [
            {
                'product_name': '测试产品',
                'brand': '测试品牌',
                'model': 'MODEL-001',
                'specs': '参数1:value1;参数2:value2',
                'min_price': 1000,
                'max_price': 1200,
                'quantity': 2,
                'overall_confidence': 85,
                'sources': [
                    {'source': '京东', 'price': 1000},
                    {'source': '天猫', 'price': 1200},
                ]
            }
        ]
        
        # 测试 Markdown
        md = gen.generate(products, '测试报告', 'markdown')
        self.assertIn('测试报告', md)
        self.assertIn('测试产品', md)
        self.assertIn('¥1,000', md)
        
        # 测试 HTML
        html = gen.generate(products, '测试报告', 'html')
        self.assertIn('<html', html)
        self.assertIn('测试产品', html)
        
        print("✓ 测试报告生成通过")


class TestSpecComparator(unittest.TestCase):
    """测试参数对比"""
    
    def test_spec_parsing(self):
        """测试规格解析"""
        from spec_compare import SpecComparator
        
        comp = SpecComparator()
        
        specs = '参数1:value1;参数2:value2;参数3'
        parsed = comp.parse_specs(specs)
        
        self.assertEqual(parsed.get('参数1'), 'value1')
        self.assertEqual(parsed.get('参数2'), 'value2')
        
        print("✓ 测试规格解析通过")
    
    def test_value_comparison(self):
        """测试值比较"""
        from spec_compare import SpecComparator
        
        comp = SpecComparator()
        
        # 数值比较
        is_match, deviation = comp.compare_values('100', '100')
        self.assertTrue(is_match)
        
        # 允许误差
        is_match, deviation = comp.compare_values('100', '105')
        self.assertTrue(is_match)
        
        print("✓ 测试值比较通过")


class TestEmailSender(unittest.TestCase):
    """测试邮件发送"""
    
    def test_email_config(self):
        """测试邮件配置"""
        from src.manufacturer import EmailSender
        
        config = {
            'smtp_host': 'smtp.qq.com',
            'smtp_port': 465,
            'smtp_ssl': True,
            'smtp_user': 'test@qq.com',
            'smtp_password': 'test',
        }
        
        sender = EmailSender(config)
        
        self.assertEqual(sender.smtp_host, 'smtp.qq.com')
        self.assertEqual(sender.smtp_port, 465)
        self.assertTrue(sender.smtp_ssl)
        
        print("✓ 测试邮件配置通过")


class TestHistoryMatcher(unittest.TestCase):
    """测试历史匹配"""
    
    def test_database_connection(self):
        """测试数据库连接"""
        from src.history import HistoryMatcher
        
        matcher = HistoryMatcher('data/history.db')
        self.assertIsNotNone(matcher.conn)
        matcher.close()
        
        print("✓ 测试数据库连接通过")
    
    def test_search(self):
        """测试搜索"""
        from src.history import HistoryMatcher
        
        matcher = HistoryMatcher('data/history.db')
        
        results = matcher.search_similar('摄像机', top_k=5)
        # 可能有结果也可能没有
        
        matcher.close()
        
        print("✓ 测试搜索通过")


class TestCharts(unittest.TestCase):
    """测试图表"""
    
    def test_bar_chart(self):
        """测试柱状图"""
        from src.charts import PriceChart
        
        chart = PriceChart(width=40)
        
        data = {'产品A': 1000, '产品B': 2000, '产品C': 1500}
        result = chart.bar_chart(data, '测试')
        
        self.assertIn('产品A', result)
        self.assertIn('产品B', result)
        self.assertIn('1,000', result)
        
        print("✓ 测试柱状图通过")
    
    def test_horizontal_bar(self):
        """测试水平柱状图"""
        from src.charts import PriceChart
        
        chart = PriceChart(width=40)
        
        items = [('A', 100), ('B', 200)]
        result = chart.horizontal_bar(items, '测试')
        
        self.assertIn('A', result)
        self.assertIn('100.0%', result)
        
        print("✓ 测试水平柱状图通过")


class TestConfigManager(unittest.TestCase):
    """测试配置管理"""
    
    def test_config_load(self):
        """测试配置加载"""
        from src.config_manager import ConfigManager
        
        config = ConfigManager()
        
        # 测试默认值
        self.assertEqual(config.config.smtp_host, 'smtp.qq.com')
        self.assertEqual(config.config.smtp_port, 465)
        
        print("✓ 测试配置加载通过")


def run_tests():
    """运行所有测试"""
    print("=" * 50)
    print("  单元测试")
    print("=" * 50)
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestReportGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestSpecComparator))
    suite.addTests(loader.loadTestsFromTestCase(TestEmailSender))
    suite.addTests(loader.loadTestsFromTestCase(TestHistoryMatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestCharts))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 汇总
    print()
    print("=" * 50)
    if result.wasSuccessful():
        print(f"  ✓ 全部通过 ({result.testsRun} 个测试)")
    else:
        print(f"  ✗ 失败 {len(result.failures)} 个, 错误 {len(result.errors)} 个")
    print("=" * 50)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
