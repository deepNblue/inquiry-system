"""
调度器模块
支持定时询价和周期更新
"""

import asyncio
from typing import List, Dict, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False


class ScheduleType(Enum):
    ONCE = "once"
    CRON = "cron"
    INTERVAL = "interval"


@dataclass
class InquiryJob:
    """询价任务"""
    id: str = ""
    name: str = ""
    products: List[Dict] = field(default_factory=list)
    methods: List[str] = field(default_factory=lambda: ["web"])  # web, manufacturer, history
    schedule_type: str = "once"
    schedule_config: Dict = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    results: Any = None
    created_at: str = ""
    updated_at: str = ""
    next_run: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class InquiryScheduler:
    """询价调度器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.scheduler = None
        self.jobs: Dict[str, InquiryJob] = {}
        self._callbacks: Dict[str, Callable] = {}
        
        if HAS_SCHEDULER:
            self.scheduler = AsyncIOScheduler()
    
    def add_job(
        self,
        job: InquiryJob,
        callback: Callable = None
    ) -> str:
        """
        添加调度任务
        
        Args:
            job: 询价任务
            callback: 执行完成后的回调函数
        
        Returns:
            任务 ID
        """
        self.jobs[job.id] = job
        
        if callback:
            self._callbacks[job.id] = callback
        
        if self.scheduler and job.schedule_type != ScheduleType.ONCE.value:
            self._schedule_job(job)
        
        return job.id
    
    def _schedule_job(self, job: InquiryJob):
        """调度任务"""
        if job.schedule_type == ScheduleType.CRON.value:
            trigger = CronTrigger(**job.schedule_config)
        elif job.schedule_type == ScheduleType.INTERVAL.value:
            trigger = IntervalTrigger(**job.schedule_config)
        else:
            return
        
        self.scheduler.add_job(
            self._execute_job,
            trigger,
            args=[job.id],
            id=job.id,
            replace_existing=True
        )
        
        # 计算下次执行时间
        job.next_run = str(trigger.get_next_fire_time())
    
    async def _execute_job(self, job_id: str):
        """执行任务"""
        job = self.jobs.get(job_id)
        if not job:
            return
        
        job.status = "running"
        job.updated_at = datetime.now().isoformat()
        
        try:
            # 这里会调用实际的询价逻辑
            # 实际执行由主程序控制
            job.status = "completed"
            
            # 执行回调
            if job_id in self._callbacks:
                callback = self._callbacks[job_id]
                if asyncio.iscoroutinefunction(callback):
                    await callback(job)
                else:
                    callback(job)
                    
        except Exception as e:
            job.status = "failed"
            print(f"Job {job_id} failed: {e}")
        
        job.updated_at = datetime.now().isoformat()
    
    def run_once(self, job: InquiryJob) -> InquiryJob:
        """立即执行单次任务"""
        job.schedule_type = ScheduleType.ONCE.value
        job.status = "running"
        job.updated_at = datetime.now().isoformat()
        
        # 同步执行（简化）
        asyncio.create_task(self._execute_job(job.id))
        
        return job
    
    def remove_job(self, job_id: str):
        """移除任务"""
        if job_id in self.jobs:
            if self.scheduler:
                self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
    
    def get_job(self, job_id: str) -> Optional[InquiryJob]:
        """获取任务"""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[InquiryJob]:
        """列出所有任务"""
        return list(self.jobs.values())
    
    def start(self):
        """启动调度器"""
        if self.scheduler:
            self.scheduler.start()
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
    
    def save_state(self, path: str):
        """保存状态"""
        data = {
            "jobs": [
                {
                    **asdict(job),
                    "results": str(job.results) if job.results else None
                }
                for job in self.jobs.values()
            ]
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_state(self, path: str):
        """加载状态"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for job_data in data.get("jobs", []):
                job = InquiryJob(**job_data)
                self.jobs[job.id] = job
                
                if job.schedule_type != ScheduleType.ONCE.value:
                    self._schedule_job(job)
                    
        except FileNotFoundError:
            pass


# 辅助函数
def asdict(obj):
    """将对象转为字典（处理 dataclass）"""
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for name, field in obj.__dataclass_fields__.items():
            value = getattr(obj, name)
            if isinstance(value, list):
                result[name] = [asdict(v) if hasattr(v, "__dataclass_fields__") else v for v in value]
            elif hasattr(value, "__dataclass_fields__"):
                result[name] = asdict(value)
            else:
                result[name] = value
        return result
    return obj
