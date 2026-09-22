const http = require('http');
const https = require('https');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');

// Configuration
const API_URL = 'http://localhost:3000';
const API_KEY = process.env.SCATTERID_API_KEY || 'test-key';
const TEST_DURATION_SEC = 30;
const CONCURRENCY = 50;

let totalRequests = 0;
let successfulRequests = 0;
let failedRequests = 0;
let latencies = [];

console.log(`Starting ScatterID Load Test for Q1 Paper Metrics...`);
console.log(`Target: ${API_URL}`);
console.log(`Duration: ${TEST_DURATION_SEC} seconds | Concurrency: ${CONCURRENCY}`);

const startTime = Date.now();

// Helper to generate a random SHA-256 hex string (simulating data hash)
function generateRandomHash() {
  return crypto.createHash('sha256').update(crypto.randomBytes(32)).digest('hex');
}

// Perform a single issuance request
function performRequest() {
  return new Promise((resolve) => {
    const dataHash = generateRandomHash();
    const payload = JSON.stringify({ dataHash });

    const reqOptions = {
      hostname: 'localhost',
      port: 3000,
      path: '/issue',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Length': Buffer.byteLength(payload)
      }
    };

    const reqStartTime = performance.now();
    
    const req = http.request(reqOptions, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const reqEndTime = performance.now();
        const latency = reqEndTime - reqStartTime;
        latencies.push(latency);
        
        if (res.statusCode === 201 || res.statusCode === 202) {
          successfulRequests++;
        } else {
          failedRequests++;
        }
        totalRequests++;
        resolve();
      });
    });

    req.on('error', (e) => {
      failedRequests++;
      totalRequests++;
      resolve();
    });

    req.write(payload);
    req.end();
  });
}

// Worker function
async function runWorker() {
  while (Date.now() - startTime < TEST_DURATION_SEC * 1000) {
    await performRequest();
  }
}

// Launch workers
async function main() {
  const workers = [];
  for (let i = 0; i < CONCURRENCY; i++) {
    workers.push(runWorker());
  }
  
  await Promise.all(workers);
  
  const endTime = Date.now();
  const actualDuration = (endTime - startTime) / 1000;
  
  // Calculate Metrics
  const tps = totalRequests / actualDuration;
  latencies.sort((a, b) => a - b);
  const p50 = latencies[Math.floor(latencies.length * 0.50)] || 0;
  const p95 = latencies[Math.floor(latencies.length * 0.95)] || 0;
  const p99 = latencies[Math.floor(latencies.length * 0.99)] || 0;
  
  console.log(`\n=== RESULTS ===`);
  console.log(`Total Requests: ${totalRequests}`);
  console.log(`Successful: ${successfulRequests}`);
  console.log(`Failed: ${failedRequests}`);
  console.log(`Throughput: ${tps.toFixed(2)} TPS`);
  console.log(`Latency P50: ${p50.toFixed(2)} ms`);
  console.log(`Latency P95: ${p95.toFixed(2)} ms`);
  console.log(`Latency P99: ${p99.toFixed(2)} ms`);
  
  // Save to CSV for Paper
  const csvData = `Metric,Value\nTotalRequests,${totalRequests}\nSuccessful,${successfulRequests}\nFailed,${failedRequests}\nThroughput(TPS),${tps.toFixed(2)}\nLatencyP50(ms),${p50.toFixed(2)}\nLatencyP95(ms),${p95.toFixed(2)}\nLatencyP99(ms),${p99.toFixed(2)}\n`;
  
  const resultsPath = require('path').join(__dirname, 'results.csv');
  fs.writeFileSync(resultsPath, csvData);
  console.log(`\nMetrics saved to ${resultsPath} for Elsevier paper plotting.`);
}

main();
