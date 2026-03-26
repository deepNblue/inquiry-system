"""
定时询价任务
支持周期性价格监控
"""

import asyncio
import os
from typing import List, Dict, Callable, Optional
from datetime import datetime
from pathlib import Path
import json

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False


class ScheduledInquiry:
    """定时询价任务"""
    
    def __init__(self, tasks_file: str = "data/scheduled_tasks.json"):
        self.tasks_file = tasks_file
        self.tasks: List[Dict] = []
        self.scheduler = AsyncIOScheduler() if HAS_SCHEDULER else None
        self._load_tasks()
    
    def _load_tasks(self):
        """加载任务"""
        if os.path.exists(self.tasks_file):
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
    
    def _save_tasks(self):
        """保存任务"""
        Path(self.tasks_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.tasks_file, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def add_task(
        self,
        name: str,
        products_file: str,
        methods: List[str] = None,
        schedule_type: str = "interval",  # interval, cron, daily
        interval_hours: int = 24,
        cron_time: str = "09:00",
        output_dir: str = "output",
        notify: bool = False,
        feishu_webhook: str = None
    ) -> str:
        """
        添加定时任务
        
        Args:
            name: 任务名称
            products_file: 产品列表文件
            schedule_type: 调度类型
            interval_hours: 间隔小时数
            cron_time: 定时时间 (HH:MM)
            ...
        
        Returns:
            任务 ID
        """
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        task = {
            "id": task_id,
            "name": name,
            "products_file": products_file,
            "methods": methods or ["web", "history"],
            "schedule_type": schedule_type,
            "interval_hours": interval_hours,
            "cron_time": cron_time,
            "output_dir": output_dir,
            "notify": notify,
            "feishu_webhook": feishu_webhook,
            "enabled": True,
            "last_run": None,
            "next_run": None,
            "created_at": datetime.now().isoformat()
        }
        
        self.tasks.append(task)
        self._save_tasks()
        
        # 注册到调度器
        if self.scheduler and task["enabled"]:
            self._schedule_task(task)
        
        return task_id
    
    def _schedule_task(self, task: Dict):
        """注册调度任务"""
        async def job():
            await self._run_task(task["id"])
        
        if task["schedule_type"] == "interval":
            trigger = IntervalTrigger(hours=task["interval_hours"])
        elif task["schedule_type"] == "cron":
            hour, minute = task["cron_time"].split(":")
            trigger = CronTrigger(hour=int(hour), minute=int(minute))
        elif task["schedule_type"] == "daily":
            hour, minute = task["cron_time"].split(":")
            trigger = CronTrigger(hour=int(hour), minute=int(minute))
        else:
            return
        
        self.scheduler.add_job(job, trigger, id=task["id"])
    
    async def _run_task(self, task_id: str):
        """执行任务"""
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            return
        
        print(f"\n{'='*50}")
        print(f"执行定时任务: {task['name']}")
        print(f"{'='*50}")
        
        # 更新最后执行时间
        task["last_run"] = datetime.now().isoformat()
        self._save_tasks()
        
        # 执行询价
        try:
            from main import InquirySystem
            
            system = InquirySystem()
            products = system.load_products(task["products_file"])
            results = await system.inquiry(products, task["methods"])
            
            # 保存结果
            output_file = f"{task['output_dir']}/{task['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            system.save_results(results, output_file)
            
            # 飞书通知
            if task.get("notify") and task.get("feishu_webhook"):
                from src.feishu_notifier import FeishuNotifier
                notifier = FeishuNotifier(webhook_url=task["feishu_webhook"])
                notifier.send_inquiry_results(results, f"定时询价: {task['name']}")
            
            print(f"任务完成: {output_file}")
            
        except Exception as e:
            print(f"任务执行失败: {e}")
    
    def remove_task(self, task_id: str):
        """移除任务"""
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self._save_tasks()
        
        if self.scheduler:
            self.scheduler.remove_job(task_id)
    
    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        return self.tasks
    
    def enable_task(self, task_id: str):
        """启用任务"""
        for task in self.tasks:
            if task["id"] == task_id:
                task["enabled"] = True
                self._save_tasks()
                if self.scheduler:
                    self._schedule_task(task)
                break
    
    def disable_task(self, task_id: str):
        """禁用任务"""
        for task in self.tasks:
            if task["id"] == task_id:
                task["enabled"] = False
                self._save_tasks()
                if self.scheduler:
                    self.scheduler.remove_job(task_id)
                break
    
    def start(self):
        """启动调度器"""
        if self.scheduler:
            # 注册所有任务
            for task in self.tasks:
                if task["enabled"]:
                    self._schedule_task(task)
            
            self.scheduler.start()
            print("定时任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
            print("定时任务调度器已停止")


# CLI 工具
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="定时询价任务管理")
    subparsers = parser.add_subparsers(dest="command")
    
    # 添加任务
    add_parser = subparsers.add_parser("add", help="添加定时任务")
    add_parser.add_argument("--name", required=True, help="任务名称")
    add_parser.add_argument("--products", required=True, help="产品列表文件")
    add_parser.add_argument("--interval", type=int, default=24, help="间隔小时数")
    add_parser.add_argument("--cron", default="09:00", help="定时时间 HH:MM")
    
    # 列出任务
    subparsers.add_parser("list", help="列出所有任务")
    
    # 启动
    subparsers.add_parser("start", help="启动调度器")
    
    args = parser.parse_args()
    
    scheduler = ScheduledInquiry()
    
    if args.command == "add":
        task_id = scheduler.add_task(
            name=args.name,
            products_file=args.products,
            interval_hours=args.interval,
            cron_time=args.cron
        )
        print(f"任务已添加: {task_id}")
    
    elif args.command == "list":
        for t in scheduler.list_tasks():
            status = "启用" if t["enabled"] else "禁用"
            print(f"[{t['id']}] {t['name']} - {status}")
    
    elif args.command == "start":
        scheduler.start()
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            scheduler.stop()
    
    else:
        parser.print_help()
