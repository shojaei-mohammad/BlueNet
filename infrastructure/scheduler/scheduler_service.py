# infrastructure/scheduler/scheduler_service.py
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from infrastructure.scheduler.scheduler import VPNAccountingService


class SchedulerService:
    def __init__(self, session_pool, bot, config):
        self.scheduler = AsyncIOScheduler()
        self.vpn_accounting = VPNAccountingService(session_pool, bot, config)
        self.config = config

    def setup_jobs(self):
        try:
            # Initialize WireGuard managers at startup
            self.scheduler.add_job(
                self.vpn_accounting.initialize_wg_managers,
                trigger="date",  # Run once at startup
                id="initialize_wg_managers",
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes grace time
                max_instances=1,
            )

            # Track first usage - check every 10 minutes
            self.scheduler.add_job(
                self.vpn_accounting.track_first_usage,
                trigger=IntervalTrigger(minutes=5),
                id="track_first_usage_job",
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes grace time
                max_instances=1,
            )

            # Update usage data - run every 30 minutes
            self.scheduler.add_job(
                self.vpn_accounting.update_usage_data,
                trigger=IntervalTrigger(minutes=10),
                id="update_usage_data_job",
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes grace time
                max_instances=1,
            )

            # Disable expired services - run every hour
            self.scheduler.add_job(
                self.vpn_accounting.disable_expired_services,
                trigger=IntervalTrigger(minutes=15),
                id="disable_expired_services_job",
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes grace time
                max_instances=1,
            )
            self.scheduler.add_job(
                self.vpn_accounting.delete_expired_services,
                trigger=IntervalTrigger(minutes=1),
                id="delete_expired_services",
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes grace time
                max_instances=1,
            )

            logging.info("Scheduler jobs have been set up successfully")
        except Exception as e:
            logging.error(f"Error setting up scheduler jobs: {str(e)}", exc_info=True)
            raise

    def start(self):
        try:
            self.setup_jobs()
            self.scheduler.start()
            logging.info("Scheduler started successfully")
        except Exception as e:
            logging.error(f"Failed to start scheduler: {str(e)}", exc_info=True)
            raise

    async def shutdown(self):
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logging.info("Scheduler shut down successfully")
        except Exception as e:
            logging.error(f"Error shutting down scheduler: {str(e)}", exc_info=True)
            raise
