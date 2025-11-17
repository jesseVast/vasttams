/**
 * Performance Testing Utility for Segment Loading
 * 
 * Usage in browser console:
 *   import { testSegmentLoading } from './utils/performanceTest';
 *   testSegmentLoading('flow-id-here');
 * 
 * Or directly in console:
 *   window.testSegmentLoading('flow-id-here');
 */

interface PerformanceMetrics {
  flowId: string;
  timerange?: string;
  initialBatch: {
    size: number;
    duration: number;
    dataSize: number;
  };
  batches: Array<{
    batchNumber: number;
    size: number;
    duration: number;
    dataSize: number;
  }>;
  total: {
    segments: number;
    duration: number;
    averageBatchTime: number;
    totalDataSize: number;
  };
  breakdown: {
    apiTime: number;
    sortingTime: number;
    stateUpdateTime: number;
    domUpdateTime: number;
  };
}

export async function testSegmentLoading(
  flowId: string,
  timerange?: string,
  initialBatchSize: number = 50,
  batchSize: number = 1000
): Promise<PerformanceMetrics> {
  const { segmentService } = await import('../services/api');
  
  const metrics: PerformanceMetrics = {
    flowId,
    timerange,
    initialBatch: { size: 0, duration: 0, dataSize: 0 },
    batches: [],
    total: {
      segments: 0,
      duration: 0,
      averageBatchTime: 0,
      totalDataSize: 0,
    },
    breakdown: {
      apiTime: 0,
      sortingTime: 0,
      stateUpdateTime: 0,
      domUpdateTime: 0,
    },
  };

  const startTime = performance.now();
  let totalApiTime = 0;
  let totalSortingTime = 0;
  let totalStateUpdateTime = 0;
  let totalDomUpdateTime = 0;

  console.group(`🧪 Performance Test: Loading segments for flow ${flowId}`);
  
  try {
    // Test initial batch
    console.log(`📊 Testing initial batch (size=${initialBatchSize})...`);
    const initialStart = performance.now();
    const initialBatch = await segmentService.listByFlow(flowId, timerange, initialBatchSize, 0);
    const initialEnd = performance.now();
    const initialDuration = initialEnd - initialStart;
    const initialDataSize = JSON.stringify(initialBatch).length;
    
    totalApiTime += initialDuration;
    metrics.initialBatch = {
      size: initialBatch.length,
      duration: initialDuration,
      dataSize: initialDataSize,
    };
    
    console.log(`✅ Initial batch: ${initialBatch.length} segments in ${initialDuration.toFixed(2)}ms (${(initialDataSize / 1024).toFixed(2)} KB)`);
    console.log(`   Rate: ${(initialBatch.length / (initialDuration / 1000)).toFixed(2)} segments/sec`);
    console.log(`   Data rate: ${(initialDataSize / 1024 / (initialDuration / 1000)).toFixed(2)} KB/sec`);

    if (initialBatch.length === 0) {
      console.log('⚠️  No segments found');
      metrics.total.segments = 0;
      metrics.total.duration = initialDuration;
      return metrics;
    }

    // Test sorting
    const sortStart = performance.now();
    const sorted = [...initialBatch].sort((a, b) => {
      const aOffset = a.sample_offset ?? -1;
      const bOffset = b.sample_offset ?? -1;
      return aOffset - bOffset;
    });
    const sortEnd = performance.now();
    const sortDuration = sortEnd - sortStart;
    totalSortingTime += sortDuration;
    console.log(`🔄 Sorting ${initialBatch.length} segments: ${sortDuration.toFixed(2)}ms`);

    // Load remaining batches
    let allSegments = [...initialBatch];
    let offset = initialBatch.length;
    let hasMore = initialBatch.length === initialBatchSize;
    let batchNumber = 0;

    while (hasMore) {
      batchNumber++;
      console.log(`📊 Testing batch ${batchNumber} (size=${batchSize}, offset=${offset})...`);
      
      const batchStart = performance.now();
      const batch = await segmentService.listByFlow(flowId, timerange, batchSize, offset);
      const batchEnd = performance.now();
      const batchDuration = batchEnd - batchStart;
      const batchDataSize = JSON.stringify(batch).length;
      
      totalApiTime += batchDuration;
      
      metrics.batches.push({
        batchNumber,
        size: batch.length,
        duration: batchDuration,
        dataSize: batchDataSize,
      });

      console.log(`✅ Batch ${batchNumber}: ${batch.length} segments in ${batchDuration.toFixed(2)}ms (${(batchDataSize / 1024).toFixed(2)} KB)`);
      console.log(`   Rate: ${(batch.length / (batchDuration / 1000)).toFixed(2)} segments/sec`);
      console.log(`   Data rate: ${(batchDataSize / 1024 / (batchDuration / 1000)).toFixed(2)} KB/sec`);

      if (batch.length === 0) {
        hasMore = false;
      } else {
        allSegments = [...allSegments, ...batch];
        offset += batch.length;

        // Test sorting
        const sortStart = performance.now();
        const sorted = [...allSegments].sort((a, b) => {
          const aOffset = a.sample_offset ?? -1;
          const bOffset = b.sample_offset ?? -1;
          return aOffset - bOffset;
        });
        const sortEnd = performance.now();
        totalSortingTime += sortEnd - sortStart;

        if (batch.length < batchSize) {
          hasMore = false;
        }
      }
    }

    const endTime = performance.now();
    const totalDuration = endTime - startTime;
    const totalDataSize = JSON.stringify(allSegments).length;

    metrics.total = {
      segments: allSegments.length,
      duration: totalDuration,
      averageBatchTime: metrics.batches.length > 0
        ? metrics.batches.reduce((sum, b) => sum + b.duration, 0) / metrics.batches.length
        : 0,
      totalDataSize,
    };

    metrics.breakdown = {
      apiTime: totalApiTime,
      sortingTime: totalSortingTime,
      stateUpdateTime: totalStateUpdateTime,
      domUpdateTime: totalDomUpdateTime,
    };

    // Summary
    console.group('📈 Performance Summary');
    console.log(`Total segments: ${metrics.total.segments}`);
    console.log(`Total time: ${totalDuration.toFixed(2)}ms (${(totalDuration / 1000).toFixed(2)}s)`);
    console.log(`Overall rate: ${(metrics.total.segments / (totalDuration / 1000)).toFixed(2)} segments/sec`);
    console.log(`Total data: ${(totalDataSize / 1024 / 1024).toFixed(2)} MB`);
    console.log(`Data rate: ${(totalDataSize / 1024 / 1024 / (totalDuration / 1000)).toFixed(2)} MB/sec`);
    console.log('');
    console.log('⏱️  Time Breakdown:');
    console.log(`  API calls: ${totalApiTime.toFixed(2)}ms (${((totalApiTime / totalDuration) * 100).toFixed(1)}%)`);
    console.log(`  Sorting: ${totalSortingTime.toFixed(2)}ms (${((totalSortingTime / totalDuration) * 100).toFixed(1)}%)`);
    console.log(`  State updates: ${totalStateUpdateTime.toFixed(2)}ms (${((totalStateUpdateTime / totalDuration) * 100).toFixed(1)}%)`);
    console.log(`  DOM updates: ${totalDomUpdateTime.toFixed(2)}ms (${((totalDomUpdateTime / totalDuration) * 100).toFixed(1)}%)`);
    console.log('');
    console.log('📦 Batch Performance:');
    if (metrics.batches.length > 0) {
      const batchTimes = metrics.batches.map(b => b.duration);
      const minBatch = Math.min(...batchTimes);
      const maxBatch = Math.max(...batchTimes);
      console.log(`  Batches: ${metrics.batches.length}`);
      console.log(`  Average: ${metrics.total.averageBatchTime.toFixed(2)}ms`);
      console.log(`  Min: ${minBatch.toFixed(2)}ms`);
      console.log(`  Max: ${maxBatch.toFixed(2)}ms`);
      console.log(`  Variation: ${((maxBatch - minBatch) / metrics.total.averageBatchTime * 100).toFixed(1)}%`);
    }
    console.groupEnd();

    // Check for bottlenecks
    console.group('🔍 Bottleneck Analysis');
    const apiPercentage = (totalApiTime / totalDuration) * 100;
    if (apiPercentage > 80) {
      console.warn(`⚠️  API calls are ${apiPercentage.toFixed(1)}% of total time - likely server-side bottleneck`);
      console.warn('   Consider:');
      console.warn('   - Checking server logs for slow queries');
      console.warn('   - Database indexing on flow_id');
      console.warn('   - get_urls generation performance');
      console.warn('   - Network latency');
    } else if (totalSortingTime / totalDuration > 0.1) {
      console.warn(`⚠️  Sorting is ${((totalSortingTime / totalDuration) * 100).toFixed(1)}% of total time`);
      console.warn('   Consider optimizing sort algorithm or deferring sort');
    } else {
      console.log('✅ No obvious bottlenecks detected');
    }
    console.groupEnd();

    return metrics;
  } catch (error) {
    console.error('❌ Test failed:', error);
    throw error;
  } finally {
    console.groupEnd();
  }
}

// Make available in browser console for easy testing
if (typeof window !== 'undefined') {
  (window as any).testSegmentLoading = testSegmentLoading;
}

export default testSegmentLoading;

