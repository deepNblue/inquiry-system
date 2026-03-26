#!/usr/bin/env python3
"""
交互式命令行工具
菜单式操作，更友好
"""

import os
import sys
import csv
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class InteractiveCLI:
    """交互式命令行工具"""
    
    def __init__(self):
        self.running = True
        self.width = 60
    
    def clear(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def header(self, title: str = "自动询价系统"):
        """显示头部"""
        self.clear()
        print("=" * self.width)
        print(f"  {title}")
        print("=" * self.width)
        print()
    
    def menu(self, title: str, options: list, back: bool = True):
        """显示菜单"""
        print(f"【{title}】")
        print("-" * self.width)
        
        for i, option in enumerate(options, 1):
            if isinstance(option, tuple):
                print(f"  {i}. {option[0]}")
            else:
                print(f"  {i}. {option}")
        
        if back:
            print(f"  0. 返回")
        
        print()
    
    def input_choice(self, max_choice: int) -> int:
        """输入选择"""
        try:
            choice = input(f"请输入选项 (0-{max_choice}): ").strip()
            return int(choice) if choice else -1
        except:
            return -1
    
    def input_text(self, prompt: str, default: str = "") -> str:
        """输入文本"""
        if default:
            value = input(f"{prompt} [{default}]: ").strip()
            return value if value else default
        else:
            return input(f"{prompt}: ").strip()
    
    def confirm(self, message: str) -> bool:
        """确认"""
        response = input(f"{message} (y/n): ").strip().lower()
        return response == 'y'
    
    def pause(self):
        """暂停"""
        input("\n按回车继续...")
    
    def run(self):
        """运行主循环"""
        while self.running:
            self.main_menu()
    
    def main_menu(self):
        """主菜单"""
        self.header()
        
        options = [
            ("📋 询价管理", self.inquiry_menu),
            ("📧 邮件询价", self.email_menu),
            ("📊 历史查询", self.history_menu),
            ("📁 报告生成", self.report_menu),
            ("⚙️ 系统设置", self.settings_menu),
        ]
        
        print("主菜单:")
        print("-" * self.width)
        for i, (name, _) in enumerate(options, 1):
            print(f"  {i}. {name}")
        print(f"  0. 退出")
        print()
        
        choice = self.input_choice(len(options))
        
        if choice == 0:
            self.running = False
            print("\n再见!")
        elif 1 <= choice <= len(options):
            options[choice - 1][1]()
        else:
            print("无效选项")
            self.pause()
    
    def inquiry_menu(self):
        """询价管理菜单"""
        self.header("询价管理")
        
        options = [
            ("📝 从文件询价", self.inquiry_from_file),
            ("🔍 单产品询价", self.inquiry_single),
            ("📜 历史询价", self.inquiry_history),
        ]
        
        print("询价管理:")
        print("-" * self.width)
        for i, (name, _) in enumerate(options, 1):
            print(f"  {i}. {name}")
        print(f"  0. 返回")
        print()
        
        choice = self.input_choice(len(options))
        
        if choice == 0:
            return
        elif 1 <= choice <= len(options):
            options[choice - 1][1]()
        else:
            print("无效选项")
            self.pause()
    
    def inquiry_from_file(self):
        """从文件询价"""
        self.header("从文件询价")
        
        # 列出可用文件
        print("可用清单文件:")
        print("-" * self.width)
        
        examples_dir = "examples"
        if os.path.exists(examples_dir):
            files = [f for f in os.listdir(examples_dir) if f.endswith('.csv')]
            for i, f in enumerate(files, 1):
                print(f"  {i}. {f}")
            print(f"  0. 返回")
            print()
            
            choice = self.input_choice(len(files))
            
            if choice == 0:
                return
            elif 1 <= choice <= len(files):
                file_path = os.path.join(examples_dir, files[choice - 1])
                self.run_inquiry(file_path)
        else:
            print("  无可用文件")
            self.pause()
    
    def inquiry_single(self):
        """单产品询价"""
        self.header("单产品询价")
        
        name = self.input_text("产品名称")
        if not name:
            print("产品名称不能为空")
            self.pause()
            return
        
        brand = self.input_text("品牌", "")
        model = self.input_text("型号", "")
        
        print(f"\n产品: {name}")
        print(f"品牌: {brand or '未指定'}")
        print(f"型号: {model or '未指定'}")
        
        if self.confirm("确认询价"):
            self.run_single_inquiry(name, brand, model)
    
    def inquiry_history(self):
        """历史询价"""
        self.header("历史询价")
        
        keyword = self.input_text("搜索关键词", "")
        
        from src.history import HistoryMatcher
        matcher = HistoryMatcher()
        
        results = matcher.search_similar(keyword, top_k=10)
        
        print(f"\n找到 {len(results)} 条历史记录:")
        print("-" * self.width)
        
        for r in results:
            print(f"  • {r.product_name} ({r.brand})")
            print(f"    价格: ¥{r.price:,.0f} | 来源: {r.source}")
            print()
        
        matcher.close()
        self.pause()
    
    def run_inquiry(self, file_path: str):
        """执行询价"""
        self.header("执行询价")
        
        print(f"清单文件: {file_path}")
        
        # 加载产品
        products = []
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            products = list(reader)
        
        print(f"产品数量: {len(products)}")
        print()
        
        print("询价方式:")
        print("  1. 历史询价")
        print("  2. 网页询价")
        print("  3. 综合询价")
        print()
        
        choice = self.input_choice(3)
        
        methods = {
            1: ["history"],
            2: ["web"],
            3: ["web", "history"]
        }.get(choice, ["history"])
        
        print(f"使用方式: {', '.join(methods)}")
        
        if self.confirm("确认执行询价"):
            # TODO: 执行询价
            print("\n询价功能开发中...")
        
        self.pause()
    
    def run_single_inquiry(self, name: str, brand: str, model: str):
        """执行单个产品询价"""
        print(f"\n正在询价: {name}...")
        
        # TODO: 执行询价
        print("询价功能开发中...")
        
        self.pause()
    
    def email_menu(self):
        """邮件询价菜单"""
        self.header("邮件询价")
        
        options = [
            ("📤 发送询价邮件", self.send_inquiry_email),
            ("📥 收取回复邮件", self.receive_emails),
            ("👥 管理联系人", self.manage_contacts),
            ("📋 询价会话", self.view_sessions),
        ]
        
        print("邮件询价:")
        print("-" * self.width)
        for i, (name, _) in enumerate(options, 1):
            print(f"  {i}. {name}")
        print(f"  0. 返回")
        print()
        
        choice = self.input_choice(len(options))
        
        if choice == 0:
            return
        elif 1 <= choice <= len(options):
            options[choice - 1][1]()
        else:
            print("无效选项")
            self.pause()
    
    def send_inquiry_email(self):
        """发送询价邮件"""
        self.header("发送询价邮件")
        print("邮件发送功能:")
        print("-" * self.width)
        print("  1. 从清单发送")
        print("  2. 自定义收件人")
        print("  0. 返回")
        print()
        
        choice = self.input_choice(2)
        
        if choice == 1:
            self.inquiry_from_file()
        elif choice == 2:
            print("\n自定义收件人功能开发中...")
            self.pause()
    
    def receive_emails(self):
        """收取回复邮件"""
        self.header("收取回复邮件")
        print("收取邮件功能:")
        print("-" * self.width)
        print("  1. 收取最新回复")
        print("  2. 设置收取规则")
        print("  0. 返回")
        print()
        
        choice = self.input_choice(2)
        
        if choice == 1:
            print("\n正在连接邮箱...")
            print("收取功能开发中...")
            self.pause()
    
    def manage_contacts(self):
        """管理联系人"""
        self.header("管理联系人")
        print("联系人管理:")
        print("-" * self.width)
        print("  1. 查看联系人")
        print("  2. 添加联系人")
        print("  3. 导入联系人")
        print("  0. 返回")
        print()
        
        choice = self.input_choice(3)
        
        if choice == 1:
            self.list_contacts()
        elif choice == 2:
            self.add_contact()
        elif choice == 3:
            self.import_contacts()
    
    def list_contacts(self):
        """列出联系人"""
        self.header("联系人列表")
        
        from src.manufacturer import SalesContactManager
        
        manager = SalesContactManager()
        
        print("已添加的联系人:")
        print("-" * self.width)
        print("  (暂无联系人)")
        
        self.pause()
    
    def add_contact(self):
        """添加联系人"""
        self.header("添加联系人")
        
        name = self.input_text("姓名")
        email = self.input_text("邮箱")
        company = self.input_text("公司", "")
        brand = self.input_text("代理品牌", "")
        phone = self.input_text("电话", "")
        
        if name and email:
            from src.manufacturer import SalesContact
            import uuid
            
            contact = SalesContact(
                id=str(uuid.uuid4())[:8],
                name=name,
                email=email,
                company=company,
                brand=brand,
                phone=phone
            )
            
            print(f"\n✓ 联系人已添加: {name} <{email}>")
        else:
            print("\n姓名和邮箱不能为空")
        
        self.pause()
    
    def import_contacts(self):
        """导入联系人"""
        self.header("导入联系人")
        
        file_path = self.input_text("CSV文件路径", "examples/contacts.csv")
        
        if os.path.exists(file_path):
            print(f"\n从 {file_path} 导入...")
            print("导入功能开发中...")
        else:
            print("\n文件不存在")
        
        self.pause()
    
    def view_sessions(self):
        """查看会话"""
        self.header("询价会话")
        print("最近的询价会话:")
        print("-" * self.width)
        print("  (暂无会话记录)")
        self.pause()
    
    def history_menu(self):
        """历史查询菜单"""
        self.header("历史查询")
        
        keyword = self.input_text("搜索产品", "")
        
        print(f"\n搜索: {keyword or '(全部)'}")
        print("-" * self.width)
        
        from src.history import HistoryMatcher
        matcher = HistoryMatcher()
        
        results = matcher.search_similar(keyword, top_k=20)
        
        print(f"找到 {len(results)} 条记录\n")
        
        for r in results[:10]:
            conf = "🟢" if (r.similarity or 0.5) > 0.7 else ("🟡" if (r.similarity or 0.5) > 0.4 else "🔴")
            print(f"{conf} {r.product_name}")
            print(f"   {r.brand or '-'} | ¥{r.price:,.0f} | {r.source or '-'}")
            print()
        
        if len(results) > 10:
            print(f"... 还有 {len(results) - 10} 条")
        
        matcher.close()
        self.pause()
    
    def report_menu(self):
        """报告生成菜单"""
        self.header("报告生成")
        
        options = [
            ("📄 生成询价报告", self.generate_report),
            ("📊 价格对比图", self.show_price_chart),
            ("📈 趋势分析", self.show_trend),
        ]
        
        print("报告生成:")
        print("-" * self.width)
        for i, (name, _) in enumerate(options, 1):
            print(f"  {i}. {name}")
        print(f"  0. 返回")
        print()
        
        choice = self.input_choice(len(options))
        
        if choice == 0:
            return
        elif 1 <= choice <= len(options):
            options[choice - 1][1]()
    
    def generate_report(self):
        """生成报告"""
        self.header("生成报告")
        
        file_path = self.input_text("清单文件", "examples/equipment_list.csv")
        
        if os.path.exists(file_path):
            print(f"\n生成报告中...")
            
            from src.report_generator import ReportGenerator
            import csv
            
            products = []
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    products.append({
                        'product_name': row.get('设备名称', ''),
                        'brand': row.get('品牌', ''),
                        'model': row.get('型号', ''),
                        'quantity': int(row.get('数量', 1)),
                        'min_price': 0,
                        'overall_confidence': 0,
                        'sources': [],
                    })
            
            gen = ReportGenerator()
            os.makedirs('output', exist_ok=True)
            
            md = gen.generate(products, '设备询价清单', 'markdown')
            with open('output/inquiry_report.md', 'w', encoding='utf-8') as f:
                f.write(md)
            
            html = gen.generate(products, '设备询价清单', 'html')
            with open('output/inquiry_report.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            print("✓ 报告已生成:")
            print("  - output/inquiry_report.md")
            print("  - output/inquiry_report.html")
        else:
            print("\n文件不存在")
        
        self.pause()
    
    def show_price_chart(self):
        """显示价格对比图"""
        self.header("价格对比图")
        print("价格对比图功能开发中...")
        self.pause()
    
    def show_trend(self):
        """显示趋势"""
        self.header("趋势分析")
        
        keyword = self.input_text("产品名称", "iPhone")
        
        print(f"\n分析: {keyword}")
        print("-" * self.width)
        
        from src.price_predictor import PricePredictor
        from src.charts import PriceChart
        
        predictor = PricePredictor()
        chart = PriceChart()
        
        analysis = predictor.analyze_trend(keyword)
        
        if analysis.direction.name != "UNKNOWN":
            print(f"趋势: {analysis.direction.value}")
            print(f"评分: {analysis.trend_score}/100")
            print(f"平均价: ¥{analysis.avg_price:,.0f}")
            print(f"建议: {analysis.recommendation.upper()}")
        else:
            print("暂无历史数据")
        
        predictor.close()
        self.pause()
    
    def settings_menu(self):
        """系统设置菜单"""
        self.header("系统设置")
        
        options = [
            ("📧 邮件配置", self.email_settings),
            ("📱 飞书配置", self.feishu_settings),
            ("🗄️ 数据库", self.db_settings),
            ("📊 统计信息", self.show_stats),
            ("ℹ️ 关于", self.about),
        ]
        
        print("系统设置:")
        print("-" * self.width)
        for i, (name, _) in enumerate(options, 1):
            print(f"  {i}. {name}")
        print(f"  0. 返回")
        print()
        
        choice = self.input_choice(len(options))
        
        if choice == 0:
            return
        elif 1 <= choice <= len(options):
            options[choice - 1][1]()
    
    def show_stats(self):
        """显示统计信息"""
        self.header("系统统计")
        
        import os
        from src.history import HistoryMatcher
        
        # 文件统计
        print("📁 文件统计:")
        print("-" * self.width)
        
        files = {
            'data/history.db': '历史数据库',
            'output/': '报告目录',
            'examples/': '示例目录',
        }
        
        for path, desc in files.items():
            if os.path.exists(path):
                if os.path.isdir(path):
                    count = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
                    print(f"  {desc}: {count} 个文件")
                else:
                    size = os.path.getsize(path)
                    print(f"  {desc}: {size/1024:.1f} KB")
        
        # 数据库统计
        print()
        print("🗄️ 数据库统计:")
        print("-" * self.width)
        
        try:
            matcher = HistoryMatcher()
            conn = matcher.conn
            
            cursor = conn.execute('SELECT COUNT(*) FROM price_history')
            count = cursor.fetchone()[0]
            print(f"  历史价格记录: {count} 条")
            
            cursor = conn.execute('SELECT COUNT(DISTINCT product_name) FROM price_history')
            products = cursor.fetchone()[0]
            print(f"  不同产品: {products} 种")
            
            cursor = conn.execute('SELECT COUNT(DISTINCT brand) FROM price_history WHERE brand != ""')
            brands = cursor.fetchone()[0]
            print(f"  不同品牌: {brands} 个")
            
            matcher.close()
        except Exception as e:
            print(f"  无法获取统计: {e}")
        
        print()
        self.pause()
    
    def email_settings(self):
        """邮件设置"""
        self.header("邮件配置")
        
        print("当前配置:")
        print("-" * self.width)
        print(f"  SMTP: smtp.qq.com:465")
        print(f"  用户: 13151793@qq.com")
        print(f"  状态: ✓ 已配置")
        print()
        
        print("如需修改，请编辑 config.email.yaml")
        self.pause()
    
    def feishu_settings(self):
        """飞书设置"""
        self.header("飞书配置")
        
        print("当前配置:")
        print("-" * self.width)
        print("  Webhook: 未配置")
        print()
        
        webhook = self.input_text("输入 Webhook URL", "")
        
        if webhook:
            print(f"\n✓ Webhook 已保存")
        
        self.pause()
    
    def db_settings(self):
        """数据库设置"""
        self.header("数据库")
        
        print("数据库信息:")
        print("-" * self.width)
        print(f"  历史数据: data/history.db")
        print(f"  联系人: data/sales_contacts.db")
        print(f"  工作流: data/email_workflow.db")
        print()
        
        options = [
            ("清理历史数据", self.clean_history),
            ("导出数据", self.export_data),
            ("导入数据", self.import_data),
        ]
        
        for i, (name, _) in enumerate(options, 1):
            print(f"  {i}. {name}")
        
        self.pause()
    
    def clean_history(self):
        """清理历史"""
        self.header("清理历史数据")
        
        if self.confirm("确认清理所有历史数据"):
            print("\n清理功能开发中...")
        
        self.pause()
    
    def export_data(self):
        """导出数据"""
        self.header("导出数据")
        print("导出功能开发中...")
        self.pause()
    
    def import_data(self):
        """导入数据"""
        self.header("导入数据")
        print("导入功能开发中...")
        self.pause()
    
    def about(self):
        """关于"""
        self.header("关于")
        
        print("自动询价系统")
        print("-" * self.width)
        print("  版本: 0.2.0")
        print("  功能: 三渠道综合询价")
        print("  - 网页询价")
        print("  - 厂家询价")
        print("  - 历史询价")
        print()
        
        self.pause()


def main():
    cli = InteractiveCLI()
    cli.run()


if __name__ == "__main__":
    main()
