"""定时任务调度器：自动执行股票列表更新和实时行情爬取"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

from backend.services.crawler.stock_list import StockListCrawler
from backend.services.crawler.stock_realtime import StockRealtimeCrawler
from backend.services.crawler.stock_daily import TencentStockDailyCrawler
from backend.services.stock_service import (
    save_stock_list,
    save_realtime_quotes,
    save_daily_batch,
    record_crawl_status,
    has_today_success_record,
)
from backend.utils.trading_day import is_trading_day
from backend.models.stock import Stock
from backend.utils.db import get_db

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """定时任务调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """配置定时任务"""
        self.scheduler.add_job(
            func=self._update_stock_list,
            trigger=CronTrigger(hour=0, minute=30, day_of_week='mon'),
            id="stock_list_update",
            name="股票列表更新（每周一）",
            replace_existing=True,
        )

        self.scheduler.add_job(
            func=self._update_realtime_quotes,
            trigger=CronTrigger(hour=15, minute='15-59/5'),
            id="realtime_quotes_update",
            name="实时行情爬取",
            replace_existing=True,
        )

        self.scheduler.add_job(
            func=self._update_daily_quotes,
            trigger=CronTrigger(hour=16, minute=0),
            id="daily_quotes_update",
            name="日线数据更新（腾讯）",
            replace_existing=True,
        )

        logger.info("定时任务配置完成: "
                    "stock_list_update (每周一00:30), "
                    "realtime_quotes_update (交易日15:15起每5分钟), "
                    "daily_quotes_update (交易日16:00)")

    def _update_stock_list(self):
        """执行股票列表更新"""
        logger.info("开始执行股票列表更新...")
        crawl_time = datetime.now()

        try:
            crawler = StockListCrawler()
            df = crawler.fetch_stock_list_df()

            if df.empty:
                record_crawl_status(
                    crawl_type="list",
                    status="failed",
                    crawl_time=crawl_time,
                    success_count=0,
                    fail_count=0,
                    error_message="获取股票列表失败：返回空数据"
                )
                return

            success_count, fail_count = save_stock_list(df)

            record_crawl_status(
                crawl_type="list",
                status="success",
                crawl_time=crawl_time,
                success_count=success_count,
                fail_count=fail_count,
            )
            logger.info(f"股票列表更新完成，成功 {success_count} 只股票")

        except Exception as e:
            logger.error(f"股票列表更新失败: {e}")
            record_crawl_status(
                crawl_type="list",
                status="failed",
                crawl_time=crawl_time,
                success_count=0,
                fail_count=0,
                error_message=str(e)
            )

    def _update_realtime_quotes(self):
        """执行实时行情爬取（带完成状态检查，失败自动重试）"""
        today = date.today()
        now = datetime.now()

        if has_today_success_record("realtime", today):
            logger.info(f"今日({today})实时行情已爬取成功，跳过")
            return

        if not is_trading_day(today):
            logger.info(f"今日({today})非交易日，标记为已完成（成功数0）")
            record_crawl_status(
                crawl_type="realtime",
                status="success",
                crawl_time=now,
                success_count=0,
                fail_count=0,
                error_message="非交易日，无需爬取"
            )
            return

        logger.info("开始执行实时行情爬取...")
        crawl_time = datetime.now()

        try:
            crawler = StockRealtimeCrawler()
            df = crawler.fetch_realtime_df()

            if df.empty:
                record_crawl_status(
                    crawl_type="realtime",
                    status="failed",
                    crawl_time=crawl_time,
                    success_count=0,
                    fail_count=0,
                    error_message="获取实时行情失败：返回空数据"
                )
                return

            success_count, fail_count = save_realtime_quotes(df, today)

            status = "success" if fail_count == 0 else "partial"
            record_crawl_status(
                crawl_type="realtime",
                status=status,
                crawl_time=crawl_time,
                success_count=success_count,
                fail_count=fail_count,
            )
            logger.info(f"实时行情爬取完成，成功 {success_count}，失败 {fail_count}")

        except Exception as e:
            logger.error(f"实时行情爬取失败: {e}")
            record_crawl_status(
                crawl_type="realtime",
                status="failed",
                crawl_time=crawl_time,
                success_count=0,
                fail_count=0,
                error_message=str(e)
            )

    def _update_daily_quotes(self):
        """执行日线数据更新（腾讯源，每日收盘后增量更新）"""
        today = date.today()
        crawl_time = datetime.now()

        if has_today_success_record("daily", today):
            logger.info(f"今日({today})日线数据已更新成功，跳过")
            return

        if not is_trading_day(today):
            logger.info(f"今日({today})非交易日，标记日线为已完成（成功数0）")
            record_crawl_status(
                crawl_type="daily",
                status="success",
                crawl_time=crawl_time,
                success_count=0,
                fail_count=0,
                error_message="非交易日，无需爬取"
            )
            return

        logger.info("开始执行日线数据更新（腾讯源）...")

        try:
            db = next(get_db())
            stocks = db.query(Stock.code).all()
            codes = [s[0] for s in stocks]
            db.close()

            if not codes:
                record_crawl_status(
                    crawl_type="daily",
                    status="failed",
                    crawl_time=crawl_time,
                    success_count=0,
                    fail_count=0,
                    error_message="没有可爬取的股票"
                )
                return

            date_str = today.strftime('%Y%m%d')
            crawler = TencentStockDailyCrawler()
            success, failed, df_list = crawler.fetch_batch(
                codes=codes,
                start_date=date_str,
                end_date=date_str,
                adjust="qfq",
            )

            if not df_list:
                record_crawl_status(
                    crawl_type="daily",
                    status="failed",
                    crawl_time=crawl_time,
                    success_count=0,
                    fail_count=len(codes),
                    error_message="所有股票爬取失败"
                )
                return

            success_stocks, fail_stocks, added, updated = save_daily_batch(df_list)

            status = "success" if failed == 0 else "partial"
            record_crawl_status(
                crawl_type="daily",
                status=status,
                crawl_time=crawl_time,
                success_count=success,
                fail_count=failed,
                error_message=f"新增{added}条，更新{updated}条"
            )
            logger.info(f"日线数据更新完成，成功 {success}，失败 {failed}，"
                        f"新增 {added} 条，更新 {updated} 条")

        except Exception as e:
            logger.error(f"日线数据更新失败: {e}")
            record_crawl_status(
                crawl_type="daily",
                status="failed",
                crawl_time=crawl_time,
                success_count=0,
                fail_count=0,
                error_message=str(e)
            )

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("定时任务调度器已关闭")

    def pause(self):
        """暂停所有任务"""
        self.scheduler.pause()
        logger.info("定时任务已暂停")

    def resume(self):
        """恢复所有任务"""
        self.scheduler.resume()
        logger.info("定时任务已恢复")

    def run_job(self, job_id: str):
        """立即执行指定任务"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.func()
                logger.info(f"立即执行任务: {job_id}")
            else:
                logger.error(f"任务不存在: {job_id}")
        except JobLookupError:
            logger.error(f"任务不存在: {job_id}")

    def get_jobs_info(self):
        """获取所有任务信息"""
        jobs = self.scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else "N/A",
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]


_crawl_scheduler_instance: Optional[CrawlScheduler] = None


def get_scheduler() -> CrawlScheduler:
    """获取调度器实例"""
    global _crawl_scheduler_instance
    if _crawl_scheduler_instance is None:
        _crawl_scheduler_instance = CrawlScheduler()
    return _crawl_scheduler_instance
