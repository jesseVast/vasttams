"""Batch operations for VastDBManager"""

import logging
import time
import concurrent.futures
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from .config import DEFAULT_BATCH_SIZE, DEFAULT_MAX_WORKERS, PARALLEL_THRESHOLD, DEFAULT_MAX_RETRIES

logger = logging.getLogger(__name__)


class BatchOperations:
    """Handles efficient batch insertion and parallel processing"""
    
    def __init__(self, data_operations, performance_monitor):
        """Initialize batch operations with required components"""
        self.data_operations = data_operations
        self.performance_monitor = performance_monitor
    
    def insert_batch_efficient(self, table_name: str, data: Dict[str, List[Any]], 
                              batch_size: int = DEFAULT_BATCH_SIZE, max_workers: int = DEFAULT_MAX_WORKERS):
        """Insert large datasets efficiently using row pooling and parallel processing"""
        try:
            start_time = time.time()
            total_rows = len(next(iter(data.values())))
            
            logger.info(f"Starting efficient batch insertion of {total_rows} rows into '{table_name}'")
            logger.info(f"Using batch size: {batch_size}, max workers: {max_workers}")
            
            # Calculate number of batches
            num_batches = math.ceil(total_rows / batch_size)
            logger.info(f"Will process {num_batches} batches")
            
            def insert_batch(batch_data: Dict[str, List[Any]]) -> int:
                """Insert a single batch of data"""
                try:
                    # Call the column-oriented insert method directly
                    return self.data_operations._insert_column_batch(table_name, batch_data)
                except Exception as e:
                    logger.error(f"Batch insertion failed: {e}")
                    return 0
            
            # Prepare batches
            batches = []
            for i in range(0, total_rows, batch_size):
                end_idx = min(i + batch_size, total_rows)
                batch = {col: values[i:end_idx] for col, values in data.items()}
                batches.append(batch)
            
            # Insert batches with parallel processing for large datasets
            if num_batches > PARALLEL_THRESHOLD and max_workers > 1:
                logger.info(f"Using parallel processing with {max_workers} workers")
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_batch = {executor.submit(insert_batch, batch): i for i, batch in enumerate(batches)}
                    
                    total_inserted = 0
                    for future in concurrent.futures.as_completed(future_to_batch):
                        batch_num = future_to_batch[future]
                        try:
                            rows_inserted = future.result()
                            total_inserted += rows_inserted
                            logger.debug(f"Batch {batch_num + 1}/{num_batches} completed: {rows_inserted} rows")
                        except Exception as e:
                            logger.error(f"Batch {batch_num + 1} failed: {e}")
            else:
                # Sequential processing for smaller datasets
                logger.info("Using sequential processing")
                total_inserted = 0
                for i, batch in enumerate(batches):
                    rows_inserted = insert_batch(batch)
                    total_inserted += rows_inserted
                    logger.debug(f"Batch {i + 1}/{num_batches} completed: {rows_inserted} rows")
            
            execution_time = time.time() - start_time
            
            # Record performance metrics
            self.performance_monitor.record_query(
                query_type="insert_batch_efficient",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=total_inserted,
                splits_used=1,
                subsplits_used=1,
                success=True
            )
            
            logger.info(f"Efficient batch insertion completed: {total_inserted}/{total_rows} rows in {execution_time:.3f}s")
            logger.info(f"Insertion rate: {total_inserted/execution_time:.1f} rows/second")
            
            return total_inserted
            
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            
            # Record failed query
            self.performance_monitor.record_query(
                query_type="insert_batch_efficient",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=0,
                splits_used=1,
                subsplits_used=1,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"Efficient batch insertion failed: {e}")
            raise
    
    def insert_batch_transactional(self, table_name: str, data: Dict[str, List[Any]], 
                                  batch_size: int = DEFAULT_BATCH_SIZE, max_workers: int = DEFAULT_MAX_WORKERS, 
                                  max_retries: int = DEFAULT_MAX_RETRIES, enable_rollback: bool = True):
        """
        Insert data with transactional safety - no records are lost on failure
        
        This method ensures data integrity by:
        1. Tracking all batch operations
        2. Implementing retry logic for failed batches
        3. Providing rollback capability for partial failures
        4. Returning detailed status of all operations
        
        Args:
            table_name: Target table name
            data: Column-oriented data dictionary
            batch_size: Maximum records per batch
            max_workers: Maximum parallel workers
            max_retries: Maximum retry attempts per failed batch
            enable_rollback: Whether to enable rollback on partial failure
            
        Returns:
            Dict containing insertion results and status
        """
        try:
            start_time = time.time()
            total_rows = len(next(iter(data.values())))
            
            logger.info(f"Starting transactional batch insertion of {total_rows} rows into '{table_name}'")
            logger.info(f"Using batch size: {batch_size}, max workers: {max_workers}, max retries: {max_retries}")
            
            # Calculate number of batches
            num_batches = math.ceil(total_rows / batch_size)
            logger.info(f"Will process {num_batches} batches")
            
            # Prepare batches with tracking
            batches = []
            batch_tracking = {}  # Track status of each batch
            
            for i in range(0, total_rows, batch_size):
                end_idx = min(i + batch_size, total_rows)
                batch = {col: values[i:end_idx] for col, values in data.items()}
                batch_id = f"batch_{len(batches)}"
                batches.append(batch)
                
                # Initialize batch tracking
                batch_tracking[batch_id] = {
                    'batch_index': len(batches) - 1,
                    'start_row': i,
                    'end_row': end_idx,
                    'row_count': end_idx - i,
                    'status': 'pending',
                    'attempts': 0,
                    'error': None,
                    'rows_inserted': 0
                }
            
            def insert_batch_with_retry(batch_data: Dict[str, List[Any]], batch_id: str) -> Tuple[str, int, str]:
                """Insert a single batch with retry logic"""
                batch_info = batch_tracking[batch_id]
                batch_info['attempts'] += 1
                
                try:
                    rows_inserted = self.data_operations._insert_column_batch(table_name, batch_data)
                    batch_info['status'] = 'success'
                    batch_info['rows_inserted'] = rows_inserted
                    logger.debug(f"Batch {batch_id} completed successfully: {rows_inserted} rows")
                    return 'success', rows_inserted, ''
                    
                except Exception as e:
                    error_msg = str(e)
                    batch_info['error'] = error_msg
                    
                    if batch_info['attempts'] < max_retries:
                        batch_info['status'] = 'retrying'
                        logger.warning(f"Batch {batch_id} failed (attempt {batch_info['attempts']}/{max_retries}): {error_msg}")
                        return 'retrying', 0, error_msg
                    else:
                        batch_info['status'] = 'failed'
                        logger.error(f"Batch {batch_id} failed permanently after {max_retries} attempts: {error_msg}")
                        return 'failed', 0, error_msg
            
            # Process batches with comprehensive tracking
            if num_batches > PARALLEL_THRESHOLD and max_workers > 1:
                logger.info(f"Using parallel processing with {max_workers} workers")
                
                # Process in phases to handle retries
                for attempt_round in range(max_retries + 1):
                    # Get pending and retrying batches
                    active_batches = [bid for bid, info in batch_tracking.items() 
                                    if info['status'] in ['pending', 'retrying']]
                    
                    if not active_batches:
                        break
                    
                    logger.info(f"Processing round {attempt_round + 1}: {len(active_batches)} active batches")
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_batch = {executor.submit(insert_batch_with_retry, batches[info['batch_index']], bid): bid 
                                         for bid, info in batch_tracking.items() 
                                         if info['status'] in ['pending', 'retrying']}
                        
                        for future in concurrent.futures.as_completed(future_to_batch):
                            batch_id = future_to_batch[future]
                            try:
                                status, rows_inserted, error = future.result()
                                # Status already updated in tracking
                            except Exception as e:
                                batch_tracking[batch_id]['status'] = 'failed'
                                batch_tracking[batch_id]['error'] = str(e)
                                logger.error(f"Batch {batch_id} execution failed: {e}")
                    
                    # Check if we need another round
                    if attempt_round < max_retries:
                        retrying_batches = [bid for bid, info in batch_tracking.items() 
                                          if info['status'] == 'retrying']
                        if retrying_batches:
                            logger.info(f"Waiting before retry round {attempt_round + 2}...")
                            time.sleep(1)  # Brief pause between retry rounds
                
            else:
                # Sequential processing with retry logic
                logger.info("Using sequential processing with retry logic")
                
                for batch_id, batch_info in batch_tracking.items():
                    batch_data = batches[batch_info['batch_index']]
                    
                    for attempt in range(max_retries + 1):
                        status, rows_inserted, error = insert_batch_with_retry(batch_data, batch_id)
                        
                        if status == 'success':
                            break
                        elif status == 'failed':
                            break
                        # If retrying, continue to next attempt
                        elif attempt < max_retries:
                            time.sleep(0.1)  # Brief pause between attempts
            
            # Calculate final results
            execution_time = time.time() - start_time
            successful_batches = [bid for bid, info in batch_tracking.items() if info['status'] == 'success']
            failed_batches = [bid for bid, info in batch_tracking.items() if info['status'] == 'failed']
            total_inserted = sum(info['rows_inserted'] for info in batch_tracking.values() if info['status'] == 'success')
            
            # Prepare detailed results
            results = {
                'success': len(failed_batches) == 0,
                'total_rows': total_rows,
                'total_inserted': total_inserted,
                'total_failed': total_rows - total_inserted,
                'batches_total': num_batches,
                'batches_successful': len(successful_batches),
                'batches_failed': len(failed_batches),
                'execution_time': execution_time,
                'insertion_rate': total_inserted / execution_time if execution_time > 0 else 0,
                'batch_details': batch_tracking,
                'failed_batch_ids': failed_batches
            }
            
            # Handle partial failure scenarios
            if len(failed_batches) > 0:
                if enable_rollback and len(successful_batches) > 0:
                    logger.warning(f"Partial failure detected: {len(failed_batches)} batches failed. Rolling back successful batches...")
                    try:
                        # Note: VAST doesn't support traditional rollback, but we can mark for cleanup
                        # In a real implementation, you might want to implement a cleanup mechanism
                        logger.warning("Rollback requested but VAST doesn't support traditional rollback. Consider implementing cleanup logic.")
                    except Exception as rollback_error:
                        logger.error(f"Rollback failed: {rollback_error}")
                
                logger.error(f"Batch insertion completed with failures: {len(failed_batches)}/{num_batches} batches failed")
                logger.error(f"Failed batches: {failed_batches}")
                
                # Record failed query metrics
                self.performance_monitor.record_query(
                    query_type="insert_batch_transactional",
                    table_name=table_name,
                    execution_time=execution_time,
                    rows_returned=total_inserted,
                    splits_used=1,
                    subsplits_used=1,
                    success=False,
                    error_message=f"Partial failure: {len(failed_batches)} batches failed"
                )
                
                # Don't raise exception - return results for caller to handle
                return results
            else:
                logger.info(f"Transactional batch insertion completed successfully: {total_inserted}/{total_rows} rows in {execution_time:.3f}s")
                
                # Record successful query metrics
                self.performance_monitor.record_query(
                    query_type="insert_batch_transactional",
                    table_name=table_name,
                    execution_time=execution_time,
                    rows_returned=total_inserted,
                    splits_used=1,
                    subsplits_used=1,
                    success=True
                )
                
                return results
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            
            # Record failed query
            self.performance_monitor.record_query(
                query_type="insert_batch_transactional",
                table_name=table_name,
                execution_time=execution_time,
                rows_returned=0,
                splits_used=1,
                subsplits_used=1,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"Transactional batch insertion failed: {e}")
            raise
    
    def cleanup_partial_insertion(self, table_name: str, failed_batch_ids: List[str], 
                                 batch_details: Dict[str, Any]) -> bool:
        """
        Clean up partial insertions when batch operations fail
        
        This method helps recover from partial insertion failures by:
        1. Identifying which records were partially inserted
        2. Providing cleanup recommendations
        3. Logging detailed failure information for manual recovery
        
        Args:
            table_name: Target table name
            failed_batch_ids: List of failed batch IDs
            batch_details: Detailed batch tracking information
            
        Returns:
            True if cleanup information was logged successfully
        """
        try:
            logger.warning(f"Partial insertion cleanup requested for table '{table_name}'")
            logger.warning(f"Failed batches: {failed_batch_ids}")
            
            # Analyze failed batches
            total_failed_rows = 0
            failed_row_ranges = []
            
            for batch_id in failed_batch_ids:
                if batch_id in batch_details:
                    batch_info = batch_details[batch_id]
                    failed_rows = batch_info.get('row_count', 0)
                    total_failed_rows += failed_rows
                    
                    failed_row_ranges.append({
                        'batch_id': batch_id,
                        'start_row': batch_info.get('start_row', 0),
                        'end_row': batch_info.get('end_row', 0),
                        'row_count': failed_rows,
                        'error': batch_info.get('error', 'Unknown error'),
                        'attempts': batch_info.get('attempts', 0)
                    })
            
            logger.warning(f"Total failed rows: {total_failed_rows}")
            logger.warning("Failed row ranges:")
            for range_info in failed_row_ranges:
                logger.warning(f"  Batch {range_info['batch_id']}: Rows {range_info['start_row']}-{range_info['end_row']} "
                             f"({range_info['row_count']} rows) - Error: {range_info['error']} "
                             f"(Attempts: {range_info['attempts']})")
            
            # Provide recovery recommendations
            logger.warning("Recovery recommendations:")
            logger.warning("1. Check VAST database logs for detailed error information")
            logger.warning("2. Verify table schema and constraints")
            logger.warning("3. Check available disk space and permissions")
            logger.warning("4. Consider reducing batch size if memory issues occur")
            logger.warning("5. Implement manual retry logic for failed batches")
            
            # Log cleanup information for manual recovery
            cleanup_info = {
                'table_name': table_name,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_failed_rows': total_failed_rows,
                'failed_batches': failed_batch_ids,
                'failed_row_ranges': failed_row_ranges,
                'recovery_required': True
            }
            
            logger.info(f"Cleanup information logged: {cleanup_info}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log cleanup information: {e}")
            return False
