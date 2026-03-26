"""
定时监控服务
周期性价格检查 + 自动告警
"""

import asyncio
import os
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False


@dataclass
class MonitorTask:
    """监控任务"""
    id: str
    name: str
    product_keywords: List[str]  # 产品关键词
    check_interval_minutes: int = 60  # 检查间隔（分钟）
    enabled: bool = True
    last_check: str = ""
    next_check: str = ""
    alert_enabled: bool = True
    
    # 数据源配置
    sources: List[str] = None  # ["jd", "taobao", "alibaba"]
    
    # 告警配置
    webhook_url: str = ""
    min_price_threshold: float = 0
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = ["jd", "taobao"]


class PriceMonitor:
    """
    价格监控服务
    周期性检查产品价格变化
    """
    
    def __init__(self, config_file: str = "data/monitor_tasks.json"):
        self.config_file = config_file
        self.tasks: Dict[str, MonitorTask] = {}
        self.scheduler = AsyncIOScheduler() if HAS_SCHEDULER else None
        self.alert_callback: Optional[Callable] = None
        self._load_tasks()
    
    def _load_tasks(self):
        """加载任务"""
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for t_data in data.get("tasks", []):
                    task = MonitorTask(**t_data)
                    self.tasks[task.id] = task
    
    def _save_tasks(self):
        """保存任务"""
        Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump({
                "tasks": [vars(t) for t in self.tasks.values()]
            }, f, ensure_ascii=False, indent=2)
    
    def add_task(
        self,
        name: str,
        product_keywords: List[str],
        check_interval_minutes: int = 60,
        **kwargs
    ) -> str:
        """添加监控任务"""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        task = MonitorTask(
            id=task_id,
            name=name,
            product_keywords=product_keywords,
            check_interval_minutes=check_interval_minutes,
            **kwargs
        )
        
        self.tasks[task_id] = task
        self._save_tasks()
        
        # 注册调度
        if self.scheduler and task.enabled:
            self._schedule_task(task)
        
        return task_id
    
    def remove_task(self, task_id: str):
        """移除任务"""
        if task_id in self.tasks:
            if self.scheduler:
                self.scheduler.remove_job(task_id)
            del self.tasks[task_id]
            self._save_tasks()
    
    def enable_task(self, task_id: str):
        """启用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self._save_tasks()
            if self.scheduler:
                self._schedule_task(self.tasks[task_id])
    
    def disable_task(self, task_id: str):
        """禁用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self._save_tasks()
            if self.scheduler:
                self.scheduler.remove_job(task_id)
    
    def list_tasks(self) -> List[MonitorTask]:
        """列出所有任务"""
        return list(self.tasks.values())
    
    def _schedule_task(self, task: MonitorTask):
        """注册调度任务"""
        if not self.scheduler:
            return
        
        async def job():
            await self._execute_task(task.id)
        
        trigger = IntervalTrigger(minutes=task.check_interval_minutes)
        
        self.scheduler.add_job(
            job,
            trigger,
            id=task.id,
            replace_existing=True
        )
    
    async def _execute_task(self, task_id: str):
        """执行监控任务"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        print(f"\n{'='*50}")
        print(f"执行监控任务: {task.name}")
        print(f"{'='*50}")
        
        task.last_check = datetime.now().isoformat()
        
        # 加载询价系统
        try:
            from main import InquirySystem
            
            system = InquirySystem()
            
            # 构造产品列表
            products = []
            for keyword in task.product_keywords:
                products.append({"name": keyword})
            
            # 执行询价
            results = await system.inquiry(products, methods=["web"])
            
            # 检查告警
            if task.alert_enabled:
                from src.webhook_alert import AlertManager
                
                alert_manager = AlertManager()
                
                for r in results:
                    if r.min_price > 0:
                        # 添加临时规则用于检查
                        alerts = await alert_manager.check_price(
                            r.product_name,
                            r.min_price,
                            brand=r.brand,
                            source=r.recommended_source
                        )
                        
                        if alerts:
                            await alert_manager.send_alerts(alerts)
                            for a in alerts:
                                print(f"  ⚠️ {a.product_name}: {a.alert_type.value}")
            
            print(f"✓ 任务完成: {len(results)} 个产品")
            
        except Exception as e:
            print(f"✗ 任务执行失败: {e}")
        
        task.next_check = (datetime.now() + timedelta(minutes=task.check_interval_minutes)).isoformat()
        self._save_tasks()
    
    def run_once(self, task_id: str):
        """立即执行一次任务"""
        asyncio.create_task(self._execute_task(task_id))
    
    def run_all_now(self):
        """立即执行所有任务"""
        for task in self.tasks.values():
            if task.enabled:
                self.run_once(task.id)
    
    def start(self):
        """启动监控服务"""
        if not self.scheduler:
            print("⚠ APScheduler 未安装，定时任务不可用")
            return
        
        # 注册所有任务
        for task in self.tasks.values():
            if task.enabled:
                self._schedule_task(task)
        
        self.scheduler.start()
        print(f"✓ 价格监控服务已启动 ({len(self.tasks)} 个任务)")
    
    def stop(self):
        """停止监控服务"""
        if self.scheduler:
            self.scheduler.shutdown()
            print("✓ 价格监控服务已停止")
    
    def set_alert_callback(self, callback: Callable):
        """设置告警回调"""
        self.alert_callback = callback


# CLI 入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="价格监控服务")
    subparsers = parser.add_subparsers(dest="command")
    
    # 启动
    start_parser = subparsers.add_parser("start", help="启动监控服务")
    
    # 添加任务
    add_parser = subparsers.add_parser("add", help="添加监控任务")
    add_parser.add_argument("--name", "-n", required=True, help="任务名称")
    add_parser.add_argument("--keywords", "-k", nargs="+", required=True, help="产品关键词")
    add_parser.add_argument("--interval", "-i", type=int, default=60, help="检查间隔(分钟)")
    add_parser.add_argument("--webhook", "-w", default="", help="Webhook URL")
    
    # 列出任务
    subparsers.add_parser("list", help="列出任务")
    
    # 立即执行
    subparsers.add_parser("run", help="立即执行所有任务")
    
    args = parser.parse_args()
    
    monitor = PriceMonitor()
    
    if args.command == "start":
        monitor.start()
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            monitor.stop()
    
    elif args.command == "add":
        task_id = monitor.add_task(
            name=args.name,
            product_keywords=args.keywords,
            check_interval_minutes=args.interval,
            webhook_url=args.webhook
        )
        print(f"✓ 任务已添加: {task_id}")
    
    elif args.command == "list":
        tasks = monitor.list_tasks()
        if not tasks:
            print("暂无监控任务")
        else:
            for t in tasks:
                status = "✓" if t.enabled else "✗"
                print(f"[{status}] {t.name}")
                print(f"    关键词: {', '.join(t.product_keywords)}")
                print(f"    间隔: {t.check_interval_minutes}分钟")
                print()
    
    elif args.command == "run":
        monitor.run_all_now()
    
    else:
        parser.print_help()
