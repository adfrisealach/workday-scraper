"""
Parallel processing module for the Workday Scraper.

This module provides controlled parallel processing capabilities with chunking
to avoid overwhelming the target servers while still maintaining good performance.
"""

import time
import math
import multiprocessing.dummy as multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm

# Import TimeoutError for specific exception handling
from concurrent.futures._base import TimeoutError as FuturesTimeoutError

from .logging_utils import get_logger

logger = get_logger()


def process_in_parallel(items, process_func, max_workers=5, chunk_size=10,
                         show_progress=True, desc="Processing", **kwargs):
    """Process items in parallel with controlled concurrency and chunking.
    
    Args:
        items (list): Items to process.
        process_func (callable): Function to process each item.
        max_workers (int): Maximum number of concurrent workers.
        chunk_size (int): Number of items to process in each chunk.
        show_progress (bool): Whether to show a progress bar.
        desc (str): Description for the progress bar.
        **kwargs: Additional keyword arguments to pass to process_func.
    
    Returns:
        list: Results of processing each item.
    """
    if not items:
        logger.warning("No items to process")
        return []
    
    results = []
    total_chunks = math.ceil(len(items) / chunk_size)
    
    logger.info(f"Processing {len(items)} items in {total_chunks} chunks with {max_workers} workers")
    
    # Process in chunks to avoid overwhelming the server
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i+chunk_size]
        chunk_num = i // chunk_size + 1
        
        logger.info(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} items)")
        
        # Process the chunk with a limited number of workers
        chunk_results = process_chunk(
            chunk, 
            process_func, 
            max_workers=min(max_workers, len(chunk)),
            show_progress=show_progress,
            desc=f"{desc} (chunk {chunk_num}/{total_chunks})",
            **kwargs
        )
        
        results.extend(chunk_results)
        
        # Wait between chunks to avoid overwhelming the server
        if chunk_num < total_chunks:
            wait_time = 2  # Reduced from 5 to 2 seconds for faster processing
            logger.debug(f"Waiting {wait_time} seconds before processing next chunk")
            time.sleep(wait_time)
    
    logger.info(f"Finished processing {len(items)} items, got {len(results)} results")
    return results


def process_chunk(items, process_func, max_workers=5, show_progress=True, desc="Processing", **kwargs):
    """Process a chunk of items in parallel.
    
    Args:
        items (list): Items to process.
        process_func (callable): Function to process each item.
        max_workers (int): Maximum number of concurrent workers.
        show_progress (bool): Whether to show a progress bar.
        desc (str): Description for the progress bar.
        **kwargs: Additional keyword arguments to pass to process_func.
    
    Returns:
        list: Results of processing each item.
    """
    results = []
    
    # Use ThreadPoolExecutor for better control and exception handling
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_item = {
            executor.submit(process_func, item, **kwargs): item 
            for item in items
        }
        
        # Process results as they complete
        if show_progress:
            with tqdm.tqdm(total=len(items), desc=desc) as pbar:
                for future in as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        result = future.result()
                        if result is not None:
                            results.append(result)
                    except (TimeoutError, FuturesTimeoutError) as te:
                        logger.error(f"Timeout error processing item: {str(te)}",
                                    extra={"item": str(item)[:100]})
                        # Sleep just enough to allow sessions to be released
                        time.sleep(5)  # Reduced from 10 to 5 seconds for faster recovery
                    except Exception as e:
                        logger.error(f"Error processing item: {str(e)}",
                                    extra={"item": str(item)[:100]})
                    finally:
                        pbar.update(1)
        else:
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error processing item: {str(e)}", 
                                extra={"item": str(item)[:100]})
    
    return results


def process_with_multiprocessing_pool(items, process_func, max_workers=5, 
                                     show_progress=True, desc="Processing", **kwargs):
    """Process items using a multiprocessing pool.
    
    This is an alternative implementation using multiprocessing.Pool instead of
    ThreadPoolExecutor. It's useful for CPU-bound tasks, but has less control
    over exceptions and cancellation.
    
    Args:
        items (list): Items to process.
        process_func (callable): Function to process each item.
        max_workers (int): Maximum number of concurrent workers.
        show_progress (bool): Whether to show a progress bar.
        desc (str): Description for the progress bar.
        **kwargs: Additional keyword arguments to pass to process_func.
    
    Returns:
        list: Results of processing each item.
    """
    results = []
    
    # Prepare arguments for each item
    args_list = [(item,) for item in items]
    kwargs_list = [kwargs for _ in items]
    
    # Process with multiprocessing pool
    with multiprocessing.Pool(min(max_workers, len(items))) as pool:
        if show_progress:
            with tqdm.tqdm(total=len(items), desc=desc) as pbar:
                for result in pool.starmap(process_func, zip(args_list, kwargs_list)):
                    if result is not None:
                        results.append(result)
                    pbar.update(1)
        else:
            for result in pool.starmap(process_func, zip(args_list, kwargs_list)):
                if result is not None:
                    results.append(result)
    
    return results


def scrape_with_controlled_parallelism(jobs_to_scrape, scrape_func, max_workers=5,
                                       chunk_size=10, show_progress=True, **kwargs):
    """Scrape jobs with controlled parallelism and chunking.
    
    This is a specialized version of process_in_parallel for job scraping.
    
    Args:
        jobs_to_scrape (list): Jobs to scrape.
        scrape_func (callable): Function to scrape each job.
        max_workers (int): Maximum number of concurrent workers.
        chunk_size (int): Number of jobs to scrape in each chunk.
        show_progress (bool): Whether to show a progress bar.
        **kwargs: Additional keyword arguments to pass to scrape_func.
    
    Returns:
        list: Results of scraping each job.
    """
    return process_in_parallel(
        jobs_to_scrape,
        scrape_func,
        max_workers=max_workers,
        chunk_size=chunk_size,
        show_progress=show_progress,
        desc="Scraping jobs",
        **kwargs
    )