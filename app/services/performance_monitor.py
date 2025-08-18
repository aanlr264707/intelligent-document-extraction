import time
import threading
import psutil
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Performance monitoring and scalability management service"""
    
    def __init__(self):
        self.metrics = {
            'processing_times': deque(maxlen=1000),
            'memory_usage': deque(maxlen=100),
            'cpu_usage': deque(maxlen=100),
            'error_counts': defaultdict(int),
            'throughput': deque(maxlen=100),
            'concurrent_requests': 0,
            'total_documents_processed': 0,
            'average_processing_time': 0.0
        }
        
        self.start_time = datetime.utcnow()
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Performance thresholds
        self.thresholds = {
            'max_processing_time': float(os.getenv('PROCESSING_TIMEOUT_SECONDS', 60)),
            'max_memory_percent': 85.0,
            'max_cpu_percent': 90.0,
            'max_concurrent_extractions': int(os.getenv('MAX_CONCURRENT_EXTRACTIONS', 5)),
            'target_throughput': 2000  # documents per hour
        }
        
        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(
            max_workers=self.thresholds['max_concurrent_extractions']
        )
        
        # Processing queue
        self.processing_queue = queue.PriorityQueue()
        self.active_tasks = {}
        
        # Alert system
        self.alerts = []
        self.alert_cooldown = {}
    
    def start_monitoring(self):
        """Start performance monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
        self.executor.shutdown(wait=True)
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Check thresholds and generate alerts
                self._check_performance_thresholds()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Update throughput metrics
                self._update_throughput_metrics()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            time.sleep(10)  # Monitor every 10 seconds
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics['cpu_usage'].append({
                'timestamp': datetime.utcnow(),
                'value': cpu_percent
            })
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics['memory_usage'].append({
                'timestamp': datetime.utcnow(),
                'value': memory.percent
            })
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _check_performance_thresholds(self):
        """Check if performance thresholds are exceeded"""
        current_time = datetime.utcnow()
        
        # Check CPU usage
        if self.metrics['cpu_usage']:
            latest_cpu = self.metrics['cpu_usage'][-1]['value']
            if latest_cpu > self.thresholds['max_cpu_percent']:
                self._generate_alert('high_cpu', f"CPU usage at {latest_cpu:.1f}%", current_time)
        
        # Check memory usage
        if self.metrics['memory_usage']:
            latest_memory = self.metrics['memory_usage'][-1]['value']
            if latest_memory > self.thresholds['max_memory_percent']:
                self._generate_alert('high_memory', f"Memory usage at {latest_memory:.1f}%", current_time)
        
        # Check concurrent requests
        if self.metrics['concurrent_requests'] >= self.thresholds['max_concurrent_extractions']:
            self._generate_alert('max_concurrent', 
                               f"Maximum concurrent extractions reached: {self.metrics['concurrent_requests']}", 
                               current_time)
        
        # Check processing times
        if self.metrics['processing_times']:
            recent_times = []
            for entry in list(self.metrics['processing_times'])[-10:]:  # Last 10 processing times
                if isinstance(entry, dict) and 'processing_time' in entry:
                    recent_times.append(entry['processing_time'])
                elif isinstance(entry, (int, float)):
                    recent_times.append(entry)
            
            if recent_times:
                avg_time = sum(recent_times) / len(recent_times)
                if avg_time > self.thresholds['max_processing_time']:
                    self._generate_alert('slow_processing', 
                                       f"Average processing time: {avg_time:.1f}s", 
                                       current_time)
    
    def _generate_alert(self, alert_type: str, message: str, timestamp: datetime):
        """Generate performance alert with cooldown"""
        # Check cooldown (don't spam the same alert)
        if alert_type in self.alert_cooldown:
            if timestamp - self.alert_cooldown[alert_type] < timedelta(minutes=5):
                return
        
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': timestamp,
            'severity': self._get_alert_severity(alert_type)
        }
        
        self.alerts.append(alert)
        self.alert_cooldown[alert_type] = timestamp
        
        logger.warning(f"Performance Alert [{alert_type}]: {message}")
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def _get_alert_severity(self, alert_type: str) -> str:
        """Get alert severity based on type"""
        severity_map = {
            'high_cpu': 'warning',
            'high_memory': 'warning',
            'max_concurrent': 'error',
            'slow_processing': 'warning',
            'system_overload': 'critical'
        }
        return severity_map.get(alert_type, 'info')
    
    def _cleanup_old_data(self):
        """Clean up old performance data"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Clean up alerts older than 24 hours
        self.alerts = [alert for alert in self.alerts 
                      if alert['timestamp'] > cutoff_time]
    
    def _update_throughput_metrics(self):
        """Update throughput metrics"""
        current_time = datetime.utcnow()
        
        # Calculate documents processed in the last hour
        hour_ago = current_time - timedelta(hours=1)
        recent_processing_times = [
            t for t in self.metrics['processing_times'] 
            if isinstance(t, dict) and t.get('timestamp', datetime.min) > hour_ago
        ]
        
        current_throughput = len(recent_processing_times)
        self.metrics['throughput'].append({
            'timestamp': current_time,
            'documents_per_hour': current_throughput
        })
    
    def record_processing_start(self, document_id: str, request_id: str) -> str:
        """Record the start of document processing"""
        task_id = f"{document_id}_{request_id}_{int(time.time())}"
        
        self.active_tasks[task_id] = {
            'document_id': document_id,
            'request_id': request_id,
            'start_time': datetime.utcnow(),
            'status': 'processing'
        }
        
        self.metrics['concurrent_requests'] += 1
        
        logger.info(f"Started processing task {task_id}")
        return task_id
    
    def record_processing_end(self, task_id: str, success: bool = True, 
                            error_message: Optional[str] = None):
        """Record the end of document processing"""
        if task_id not in self.active_tasks:
            logger.warning(f"Task {task_id} not found in active tasks")
            return
        
        task = self.active_tasks[task_id]
        end_time = datetime.utcnow()
        processing_time = (end_time - task['start_time']).total_seconds()
        
        # Record processing time
        self.metrics['processing_times'].append({
            'task_id': task_id,
            'processing_time': processing_time,
            'timestamp': end_time,
            'success': success
        })
        
        # Update counters
        self.metrics['concurrent_requests'] = max(0, self.metrics['concurrent_requests'] - 1)
        self.metrics['total_documents_processed'] += 1
        
        # Update average processing time
        recent_times = [
            t['processing_time'] for t in self.metrics['processing_times']
            if isinstance(t, dict) and 'processing_time' in t
        ]
        if recent_times:
            self.metrics['average_processing_time'] = sum(recent_times) / len(recent_times)
        
        # Record errors
        if not success and error_message:
            self.metrics['error_counts'][error_message] += 1
        
        # Clean up active task
        del self.active_tasks[task_id]
        
        logger.info(f"Completed processing task {task_id} in {processing_time:.2f}s (success: {success})")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        current_time = datetime.utcnow()
        uptime = (current_time - self.start_time).total_seconds()
        
        # Calculate recent averages
        recent_cpu = []
        recent_memory = []
        
        if self.metrics['cpu_usage']:
            recent_cpu = [m['value'] for m in list(self.metrics['cpu_usage'])[-10:]]
        
        if self.metrics['memory_usage']:
            recent_memory = [m['value'] for m in list(self.metrics['memory_usage'])[-10:]]
        
        # Calculate throughput
        current_throughput = 0
        if self.metrics['throughput']:
            latest_throughput = self.metrics['throughput'][-1]
            current_throughput = latest_throughput['documents_per_hour']
        
        return {
            'system_metrics': {
                'uptime_seconds': uptime,
                'cpu_usage_percent': sum(recent_cpu) / len(recent_cpu) if recent_cpu else 0,
                'memory_usage_percent': sum(recent_memory) / len(recent_memory) if recent_memory else 0,
                'concurrent_requests': self.metrics['concurrent_requests'],
                'active_tasks': len(self.active_tasks)
            },
            'processing_metrics': {
                'total_documents_processed': self.metrics['total_documents_processed'],
                'average_processing_time': self.metrics['average_processing_time'],
                'current_throughput_per_hour': current_throughput,
                'target_throughput_per_hour': self.thresholds['target_throughput'],
                'error_count': sum(self.metrics['error_counts'].values())
            },
            'performance_status': self._get_performance_status(),
            'recent_alerts': self.alerts[-10:] if self.alerts else [],
            'thresholds': self.thresholds
        }
    
    def _get_performance_status(self) -> str:
        """Get overall performance status"""
        # Check if any critical alerts are active
        recent_alerts = [a for a in self.alerts[-10:] if a['severity'] in ['error', 'critical']]
        if recent_alerts:
            return 'degraded'
        
        # Check resource usage
        if self.metrics['cpu_usage'] and self.metrics['memory_usage']:
            latest_cpu = self.metrics['cpu_usage'][-1]['value']
            latest_memory = self.metrics['memory_usage'][-1]['value']
            
            if latest_cpu > 80 or latest_memory > 80:
                return 'high_load'
        
        # Check concurrent load
        if self.metrics['concurrent_requests'] >= self.thresholds['max_concurrent_extractions'] * 0.8:
            return 'high_load'
        
        return 'healthy'
    
    def get_processing_queue_status(self) -> Dict[str, Any]:
        """Get current processing queue status"""
        return {
            'queue_size': self.processing_queue.qsize(),
            'active_tasks': len(self.active_tasks),
            'max_concurrent': self.thresholds['max_concurrent_extractions'],
            'available_slots': max(0, self.thresholds['max_concurrent_extractions'] - self.metrics['concurrent_requests'])
        }
    
    def can_process_request(self) -> bool:
        """Check if system can handle another processing request"""
        return self.metrics['concurrent_requests'] < self.thresholds['max_concurrent_extractions']
    
    def submit_processing_task(self, task_function, *args, priority: int = 1, **kwargs):
        """Submit a processing task with priority"""
        if not self.can_process_request():
            raise Exception("Maximum concurrent extractions reached. Please try again later.")
        
        future = self.executor.submit(task_function, *args, **kwargs)
        return future
    
    def get_detailed_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """Get detailed metrics for the specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter recent data
        recent_processing = [
            t for t in self.metrics['processing_times']
            if isinstance(t, dict) and t.get('timestamp', datetime.min) > cutoff_time
        ]
        
        recent_cpu = [
            m for m in self.metrics['cpu_usage']
            if m['timestamp'] > cutoff_time
        ]
        
        recent_memory = [
            m for m in self.metrics['memory_usage']
            if m['timestamp'] > cutoff_time
        ]
        
        # Calculate statistics
        processing_times = [t['processing_time'] for t in recent_processing if 'processing_time' in t]
        success_rate = 0
        if recent_processing:
            successful = sum(1 for t in recent_processing if t.get('success', False))
            success_rate = successful / len(recent_processing)
        
        return {
            'time_period_hours': hours,
            'processing_stats': {
                'total_processed': len(recent_processing),
                'success_rate': success_rate,
                'average_time': sum(processing_times) / len(processing_times) if processing_times else 0,
                'min_time': min(processing_times) if processing_times else 0,
                'max_time': max(processing_times) if processing_times else 0
            },
            'resource_stats': {
                'cpu_usage': {
                    'average': sum(m['value'] for m in recent_cpu) / len(recent_cpu) if recent_cpu else 0,
                    'max': max(m['value'] for m in recent_cpu) if recent_cpu else 0,
                    'data_points': len(recent_cpu)
                },
                'memory_usage': {
                    'average': sum(m['value'] for m in recent_memory) / len(recent_memory) if recent_memory else 0,
                    'max': max(m['value'] for m in recent_memory) if recent_memory else 0,
                    'data_points': len(recent_memory)
                }
            },
            'error_summary': dict(self.metrics['error_counts'])
        }
    
    def optimize_performance(self) -> Dict[str, Any]:
        """Analyze performance and suggest optimizations"""
        metrics = self.get_performance_metrics()
        suggestions = []
        
        # Analyze CPU usage
        if metrics['system_metrics']['cpu_usage_percent'] > 80:
            suggestions.append({
                'type': 'cpu_optimization',
                'priority': 'high',
                'suggestion': 'Consider reducing concurrent extractions or upgrading CPU',
                'details': f"Current CPU usage: {metrics['system_metrics']['cpu_usage_percent']:.1f}%"
            })
        
        # Analyze memory usage
        if metrics['system_metrics']['memory_usage_percent'] > 80:
            suggestions.append({
                'type': 'memory_optimization',
                'priority': 'high',
                'suggestion': 'Consider increasing available memory or optimizing processing',
                'details': f"Current memory usage: {metrics['system_metrics']['memory_usage_percent']:.1f}%"
            })
        
        # Analyze processing times
        if metrics['processing_metrics']['average_processing_time'] > 30:
            suggestions.append({
                'type': 'processing_optimization',
                'priority': 'medium',
                'suggestion': 'Consider optimizing extraction algorithms or using faster models',
                'details': f"Average processing time: {metrics['processing_metrics']['average_processing_time']:.1f}s"
            })
        
        # Analyze throughput
        current_throughput = metrics['processing_metrics']['current_throughput_per_hour']
        target_throughput = metrics['processing_metrics']['target_throughput_per_hour']
        
        if current_throughput < target_throughput * 0.7:
            suggestions.append({
                'type': 'throughput_optimization',
                'priority': 'medium',
                'suggestion': 'Consider increasing concurrent processing or optimizing bottlenecks',
                'details': f"Current throughput: {current_throughput}/hour (target: {target_throughput}/hour)"
            })
        
        # Analyze error rates
        error_count = metrics['processing_metrics']['error_count']
        total_processed = metrics['processing_metrics']['total_documents_processed']
        
        if total_processed > 0:
            error_rate = error_count / total_processed
            if error_rate > 0.05:  # More than 5% error rate
                suggestions.append({
                    'type': 'reliability_optimization',
                    'priority': 'high',
                    'suggestion': 'Investigate and fix sources of processing errors',
                    'details': f"Error rate: {error_rate:.1%} ({error_count}/{total_processed})"
                })
        
        if not suggestions:
            suggestions.append({
                'type': 'status',
                'priority': 'info',
                'suggestion': 'System performance is within acceptable ranges',
                'details': 'No immediate optimizations required'
            })
        
        return {
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'performance_status': metrics['performance_status'],
            'suggestions': suggestions,
            'current_metrics': metrics
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
